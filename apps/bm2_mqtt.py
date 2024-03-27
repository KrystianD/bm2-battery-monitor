import argparse
import asyncio
import logging

from paho.mqtt.publish import single

from bm2.client import BM2Client

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


async def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--mqtt-host', type=str, metavar="HOST", default="127.0.0.1")
    argparser.add_argument('--mqtt-port', type=int, metavar="PORT", default=1883)
    argparser.add_argument('--mqtt-topic', type=str, metavar="TOPIC", default="bm2")
    argparser.add_argument('--bm2-addr', type=str, metavar="ADDR", required=True)
    args = argparser.parse_args()

    mqtt_topic = args.mqtt_topic
    mqtt_port = args.mqtt_port
    mqtt_hostname = args.mqtt_host

    bm2 = BM2Client(args.bm2_addr)
    bm2.start()

    while True:
        voltage = await bm2.get_voltage()
        payload = f"{voltage:.2f}"
        single(payload=payload, topic=mqtt_topic, port=mqtt_port, hostname=mqtt_hostname)


asyncio.run(main())
