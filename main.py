import asyncio
from config import address, parse_categories_urls, proxies
from parser.okey_parser import OKEYParser


async def main():
    parser = OKEYParser(address, parse_categories_urls, proxies)
    await parser.parse()
    await parser.close()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
