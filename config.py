from utils.proxies import get_proxies_from_file

proxies = get_proxies_from_file("proxies.txt")
csv_file = "store_data.csv"
address = "Москва, Пушкина 9А"
parse_categories_urls = [
    "/rastitel-nye-masla-sousy-i-pripravy/spetsii-pripravy",
    "/bakaleia-i-konservy/sakhar-i-sol-",
    "/ovoshchi-i-frukty/ovoshchi"
]
