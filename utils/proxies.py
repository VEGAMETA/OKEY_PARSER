import config
import curl_cffi.requests


def get_proxy() -> dict[str, str]:
    """
    Returns and rotating proxies
    :return: proxy
    """
    try:
        proxy = config.proxies.pop(0)
        config.proxies.append(proxy)
        return proxy
    except IndexError:
        ...


def check_proxy(proxy) -> bool:
    """
    Checking proxy for validity
    :param proxy:
    :return: validity
    """
    try:
        response = curl_cffi.requests.get("https://api.ipify.org?format=json", proxies=proxy)
        # print(f"valid proxy at {response.json().get('ip')}")
        return True
    except Exception as e:
        # print(f"invalid proxy at {proxy}")
        print(e)
        return False


def get_proxies_from_file(filename, proxy_format="http") -> list[dict[str, str]]:
    """
    Gets proxies from file and transforms they to valid format (from ip:port:user:pass to user:pass@ip:port)
    :param filename: proxies filename or location
    :param proxy_format: format of proxies (http by default)
    :return: list of valid proxies
    """
    proxies = []
    with open(filename) as file:
        for proxy in file:
            if proxy == "":
                continue
            proxy = proxy.strip().split("@")
            proxy = list(map(lambda x: x.split(":"), proxy))
            proxy = {"https": f"{proxy_format}://{proxy[1][0]}:{proxy[1][1]}@{proxy[0][0]}:{proxy[0][1]}"}
            if check_proxy(proxy):
                proxies.append(proxy)
    return proxies
