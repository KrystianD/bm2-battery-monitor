import argparse
import asyncio
import logging

from bm2.client import BM2Client

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


async def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--bm2-addr', type=str, metavar="ADDR", required=True)
    args = argparser.parse_args()

    bm2 = BM2Client(args.bm2_addr)
    bm2.start()

    await bm2.wait_for_connected()

    history_readings = await bm2.get_history()
    for history_reading in history_readings:
        date_str = history_reading.date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{date_str} = {history_reading.voltage} V")


asyncio.run(main())
