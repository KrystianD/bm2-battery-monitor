import argparse
import asyncio
import logging

from bm2.client import BM2Client
from bm2.transports.TransportBleak import TransportBleak

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


async def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--bm2-addr', type=str, metavar="ADDR", required=True)
    args = argparser.parse_args()

    transport = await TransportBleak.connect(args.bm2_addr)
    bm2 = BM2Client(transport)

    history_readings = await bm2.get_history()
    for history_reading in history_readings:
        date_str = history_reading.date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{date_str} = {history_reading.voltage} V")


asyncio.run(main())
