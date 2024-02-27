import re
import random
import config
import asyncio
import urllib.parse
import curl_cffi.requests
from utils.csv import save_to_csv
from utils.proxies import get_proxy
from utils.cookies import get_spid_spsc_cookies_from_html


class Parser:
    """
    Okey's parser class
    """

    def __init__(self) -> None:
        """
        Initializes asynchronous session and lock, base Okey's urls, proxies cookies and misc
        """
        self.session = curl_cffi.requests.AsyncSession(impersonate='chrome120', verify=False)
        self.lock = asyncio.Lock()
        self.proxies_cookies = {proxy.get("https"): {} for proxy in config.proxies}
        self.base_url = "https://www.okeydostavka.ru/"
        self.base_api_url: str = self.base_url + "wcs/resources/mobihub023/"
        self.cookies = {}
        self.data: list[list] = [["store_address", "category", "name", "url", "picture_url", "price", "no_sale_price"]]

    async def close(self) -> None:
        """
        Closes asynchronous session
        :return:
        """
        await self.session.close()

    async def parse(self) -> None:
        """
        Parser main logic
        - sets store info to cookies
        - runs asynchronously all url categories parsing logic
        - saves data to csv file
        :return:
        """
        await self.set_store_info_cookies()
        parse_tasks = [self.parse_categories(category) for category in config.parse_categories_urls]
        await asyncio.gather(*parse_tasks)
        save_to_csv(self.data)

    async def parse_categories(self, category_url) -> None:
        """
        Category parser
        - gets first html response
        - forms url for tasks (beginIndex is always multiple of 72 for simplicity)
        - runs pagination tasks
        :param category_url: needed category url (not from api)
        :return:
        """
        category_id = await self.get_category_id(self.base_url + self.cookies.get("storeGroup")[:3] + category_url)
        url = (
                self.base_url +
                "webapp/wcs/stores/servlet/ProductListingView" +
                "?storeId=" + self.cookies.get("storeId") +
                "&categoryId=" + category_id +
                "&beginIndex="
        )
        paginate_tasks = [self.paginate(url + str(n * 72)) for n in range(1, random.randint(2, 3))]
        await asyncio.gather(*paginate_tasks)

    async def paginate(self, formed_url) -> None:
        """
        Parse paginated responses
        :param formed_url: url is for api that loads each next page (the first one doesn't count)
        :return:
        """
        response = await self.get_response_with_proxy_cookies(formed_url, 'POST')
        html = response.text
        await self.extend_item_data_from_html(html)

    async def _get_base_store_info_from_location(self) -> dict:
        """
        Gets base store info through Okey's api (and yandex api inside)
        :return: main store info in dict format (ffcId, storeId, storeGroup)
        """
        url = self.base_api_url + "store/0/address/find?address=" + urllib.parse.quote_plus(config.address)
        response = await self.get_response_with_proxy_cookies(url)
        json_data = response.json()
        store_data = json_data.get("addresses")
        if not store_data:
            raise ValueError("Incorrect address")
        store_info = store_data[0].get("addressDeliveryStores")[0]
        if not store_info:
            raise ValueError("Probably incorrect address")
        return store_info

    async def _get_extended_store_info_from_ffc_id(self, ffc_id) -> dict:
        """
        Gets extended info about store from ffcId using basic api
        :param ffc_id: ffcId from base store info
        :return: extended store info in dict format (address, catalogId, ffcId, storeId, storeGroup)
        """
        url = self.base_api_url + "stores?ffcId=" + ffc_id
        response = await self.get_response_with_proxy_cookies(url)
        json_data = response.json()
        return json_data

    async def get_response_with_proxy_cookies(self, url, method='GET', data=None) -> curl_cffi.requests.Response:
        """
        Forms cookies for request, if there is response for
        :param url:
        :param method:
        :param data:
        :return:
        """
        proxy = get_proxy()
        while True:
            cookies = {}
            cookies.update(self.cookies)
            cookies.update(self.proxies_cookies.get(proxy.get("https")))
            if method == 'POST':
                response = await self.session.post(url, data, proxies=proxy, cookies=cookies)
            else:
                response = await self.session.get(url, proxies=proxy, cookies=cookies)
            try:
                spid, spsc = get_spid_spsc_cookies_from_html(response.text)
                self.proxies_cookies.update({proxy.get("https"): {"spid": spid, "spsc": spsc}})
                continue
            except ValueError:
                return response

    async def set_store_info_cookies(self) -> None:
        """
        Sets store info to cookies
        :return:
        """
        store_info = await self._get_base_store_info_from_location()
        ffc_id = str(store_info.get("ffcId"))
        store_info = await self._get_extended_store_info_from_ffc_id(ffc_id)
        self.cookies.update(
            {
                "storeGroup": store_info.get("storeGroup"),
                "ffcId": store_info.get("ffcId"),
                "storeId": store_info.get('storeId'),
                "selectedStore": f"{store_info.get('storeId')}_{store_info.get('ffcId')}",
                "address": store_info.get("address")
            }
        )

    async def extend_item_data_from_html(self, html) -> None:
        """
        Main parsing mechanism based on regex, parsed information extends data field with async lock
        :param html:
        :return:
        """
        category_pattern = re.compile(r'category: \"(.*?)\"')
        name_pattern = re.compile(r'name: \"(.*?)\"')
        url_pattern = re.compile(r'url:\'/(.*?)\'')
        picture_url_pattern = re.compile(r'/(wcsstore/OKMarketCAS/cat_entries/\d+/\d+.thumbnail.jpg)')
        price_pattern = re.compile(r'price label [^\"]*\">\s*(\d*,\d*)+[^<]*</span>\s*<input')
        no_sale_price_pattern = re.compile(r'crossed\">\s*(?:(\d*,\d*)+[\s₽^<]*)?</(?:[^<]*<){3}input')

        categories = category_pattern.findall(html)
        names = name_pattern.findall(html)
        urls = url_pattern.findall(html)
        picture_urls = picture_url_pattern.findall(html)
        prices = price_pattern.findall(html)
        no_sale_prices = no_sale_price_pattern.findall(html)
        everything = (categories, names, urls, picture_urls, prices, no_sale_prices)

        if not all(everything) and "CatalogEntryList" not in html and html.strip() != "":
            raise ValueError("Cannot get Items. Something went wrong")

        no_sale_prices = [value if value else prices[n] for n, value in enumerate(no_sale_prices)]
        no_sale_prices = map(lambda price: price.replace(",", "."), no_sale_prices)
        prices = map(lambda price: price.replace(",", "."), prices)
        urls = [self.base_url + url for url in urls]
        picture_urls = [self.base_url + url for url in picture_urls]
        store_addresses = [self.cookies.get("address")] * len(names)

        items_data = list(zip(store_addresses, categories, names, urls, picture_urls, prices, no_sale_prices))

        await self.lock.acquire()
        self.data.extend(items_data)
        self.lock.release()

    async def get_category_id(self, url) -> str:
        """
        Parses category_id from main category page, and also extends items from this page
        :param url: category main url
        :return: categoryId
        """
        response = await self.get_response_with_proxy_cookies(url)
        html = response.text
        category_id_pattern = re.compile(r'WCParamJS.categoryId = \"(\d*)\"')
        category_id_match = category_id_pattern.search(html)
        if not category_id_match:
            raise ValueError("Cannot get categoryID. Something went wrong")
        await self.extend_item_data_from_html(html)
        return category_id_match.group(1)
