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

    while True:
        voltage = await bm2.get_voltage()
        print(voltage)


asyncio.run(main())
