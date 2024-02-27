import asyncio
from parser.parser import Parser


async def main():
    parser = Parser()
    await parser.parse()
    await parser.close()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
