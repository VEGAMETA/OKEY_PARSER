import config
import curl_cffi.requests


def get_proxy():
    try:
        proxy = config.proxies.pop(0)
        config.proxies.append(proxy)
        return proxy
    except IndexError:
        ...


def check_proxy(proxy):
    try:
        curl_cffi.requests.get("https://api.ipify.org?format=json", proxies=proxy)
        return True
    except Exception as e:
        print(e)
        return False


def get_proxies_from_file(file):
    proxies = []
    with open("proxies.txt") as file:
        for proxy in file:
            proxy = proxy.strip().split("@")
            proxy = list(map(lambda x: x.split(":"), proxy))
            proxy = {"https": f"http://{proxy[1][0]}:{proxy[1][1]}@{proxy[0][0]}:{proxy[0][1]}"}
            if check_proxy(proxy):
                proxies.append(proxy)
    return proxies
