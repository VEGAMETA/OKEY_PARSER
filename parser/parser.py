import re
import random
from copy import copy

import config
import asyncio
import urllib.parse
import curl_cffi.requests
from utils.csv import save_to_csv
from utils.proxies import get_proxy
from utils.cookies import get_spid_spsc_cookies_from_html


class Parser:
    def __init__(self) -> None:
        self.session = curl_cffi.requests.AsyncSession(impersonate='chrome120', verify=False)
        self.lock = asyncio.Lock()
        self.proxies_cookies = {proxy.get("https"): {} for proxy in config.proxies}
        self.base_url = "https://www.okeydostavka.ru/"
        self.base_api_url: str = self.base_url + "wcs/resources/mobihub023/"
        self.address_url: str = (self.base_api_url +
                                 "store/0/address/find?address=" +
                                 urllib.parse.quote_plus(config.address)
                                 )
        self.store_info_url: str = self.base_api_url + "stores?ffcId="

        self.store_info: dict = {}
        self.store_name: str = ''
        self.cookies = {}
        self.data: list[list] = [["store_address", "category", "name", "url", "picture_url", "price", "no_sale_price"]]

    async def close(self) -> None:
        await self.session.close()

    async def parse(self) -> None:
        await self.set_store_info()
        self.set_store_cookies()
        parse_tasks = [self.parse_categories(category) for category in config.parse_categories_urls]
        await asyncio.gather(*parse_tasks)
        save_to_csv(self.data)

    async def parse_categories(self, category_url) -> None:
        category_id = await self.get_category_id(self.base_url + self.store_name + category_url)
        url = (
                self.base_url +
                "webapp/wcs/stores/servlet/ProductListingView" +
                "?storeId=" + self.store_info.get("storeId") +
                "&categoryId=" + category_id +
                "&beginIndex="
        )
        paginate_tasks = [self.paginate(url + str(n * 72)) for n in range(1, random.randint(2, 3))]
        await asyncio.gather(*paginate_tasks)

    async def paginate(self, formed_url):
        response = await self.get_response_with_proxy_cookies(formed_url, 'POST')
        html = response.text
        await self.extend_item_data_from_html(html)

    async def _get_base_store_info_from_location(self) -> dict:
        response = await self.get_response_with_proxy_cookies(self.address_url)
        json_data = response.json()
        store_data = json_data.get("addresses")
        if not store_data:
            raise ValueError("Incorrect address")
        store_info = store_data[0].get("addressDeliveryStores")[0]
        if not store_info:
            raise ValueError("Probably incorrect address")
        return store_info  # ffcId, storeId, storeGroup

    async def _get_extended_store_info_from_base(self) -> dict:
        url = self.store_info_url + str(self.store_info.get("ffcId"))
        response = await self.get_response_with_proxy_cookies(url)
        json_data = response.json()
        return json_data  # address, catalogId, ffcId, storeId, storeGroup

    async def get_response_with_proxy_cookies(self, url, method='GET', data=None):
        proxy = get_proxy()
        while True:
            cookies = {}
            cookies.update(copy(self.cookies))
            cookies.update(copy(self.proxies_cookies.get(proxy.get("https"))))
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

    async def set_store_info(self) -> None:
        self.store_info = await self._get_base_store_info_from_location()
        self.store_info = await self._get_extended_store_info_from_base()

    def set_store_cookies(self):
        self.cookies.update(
            {
                "storeGroup": self.store_info.get("storeGroup"),
                "ffcId": self.store_info.get("ffcId"),
                "selectedStore": f"{self.store_info.get('storeId')}_{self.store_info.get('ffcId')}",
            }
        )
        self.store_name = self.store_info.get("storeGroup")[:3]

    async def extend_item_data_from_html(self, html) -> None:
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
            print(html)
            print(everything)
            raise ValueError("Something went wrong")

        no_sale_prices = [value if value else prices[n] for n, value in enumerate(no_sale_prices)]
        no_sale_prices = map(lambda x: x.replace(",", "."), no_sale_prices)
        prices = map(lambda x: x.replace(",", "."), prices)
        urls = [self.base_url + url for url in urls]
        picture_urls = [self.base_url + url for url in picture_urls]

        store_names = [self.store_info.get("address")] * len(names)

        items_data = list(zip(store_names, categories, names, urls, picture_urls, prices, no_sale_prices))
        await self.lock.acquire()
        self.data.extend(items_data)
        self.lock.release()

    async def get_category_id(self, url) -> str:
        response = await self.get_response_with_proxy_cookies(url)
        html = response.text
        category_id_pattern = re.compile(r'WCParamJS.categoryId = \"(\d*)\"')
        category_id_match = category_id_pattern.search(html)
        if not category_id_match:
            raise ValueError("Something went wrong")
        await self.extend_item_data_from_html(html)
        return category_id_match.group(1)
