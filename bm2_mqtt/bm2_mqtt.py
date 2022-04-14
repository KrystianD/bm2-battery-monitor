import argparse
import asyncio
import logging
import struct
import subprocess

from bleak import BleakClient
import bleak.exc

from Crypto.Cipher import AES

from paho.mqtt.publish import single

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

KEY = b"\x6c\x65\x61\x67\x65\x6e\x64\xff\xfe\x31\x38\x38\x32\x34\x36\x36"

UUID_KEY_READ = "0000fff4-0000-1000-8000-00805f9b34fb"

mqtt_topic = ""
mqtt_port = 1883
mqtt_hostname = ""


def create_aes():
    return AES.new(KEY, AES.MODE_CBC, bytes([0] * 16))


def notification_handler(_, data: bytearray):
    encrypted_data = data
    decrypted_data = create_aes().decrypt(bytes(encrypted_data))

    if decrypted_data[0] == 0xf5:
        voltage = (struct.unpack(">H", decrypted_data[1:1 + 2])[0] >> 4) / 100
        payload = f"{voltage:.2f}"
        single(payload=payload, topic=mqtt_topic, port=mqtt_port, hostname=mqtt_hostname)


async def main():
    global mqtt_topic
    global mqtt_port
    global mqtt_hostname

    argparser = argparse.ArgumentParser()
    argparser.add_argument('--mqtt-host', type=str, metavar="HOST", default="127.0.0.1")
    argparser.add_argument('--mqtt-port', type=int, metavar="PORT", default=1883)
    argparser.add_argument('--mqtt-topic', type=str, metavar="TOPIC", default="bm2")
    argparser.add_argument('--bm2-addr', type=str, metavar="ADDR", required=True)
    args = argparser.parse_args()

    mqtt_topic = args.mqtt_topic
    mqtt_port = args.mqtt_port
    mqtt_hostname = args.mqtt_host
    bm2_addr = args.bm2_addr

    while True:
        try:
            async with BleakClient(bm2_addr) as client:
                logging.info(f"Connected")

                await client.start_notify(UUID_KEY_READ, notification_handler)

                while True:
                    if not client.is_connected:
                        break
                    await asyncio.sleep(1)

        except bleak.exc.BleakError as e:
            if "was not found" in e.args[0]:
                logging.info("Performing forceful device disconnection")
                subprocess.run("bluetoothctl", input=f"disconnect {bm2_addr}".encode("ascii"), stdout=subprocess.DEVNULL)
            elif "org.freedesktop.DBus.Error.NoReply" in e.args[0]:
                pass
            else:
                logging.error(e)
        except OSError as e:
            logging.error(e)
        finally:
            await asyncio.sleep(1)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.run_forever()
