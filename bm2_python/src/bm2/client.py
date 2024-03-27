import asyncio
import binascii
import enum
import logging
import struct
import subprocess
from asyncio import Task
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import List, Optional, Any

from bleak import BleakClient
import bleak.exc

from bm2.bit_utils import decode_3bytes, decode_nibbles
from bm2.encryption import encrypt, decrypt

logger = logging.getLogger("bm2_client")

UUID_KEY_READ = "0000fff4-0000-1000-8000-00805f9b34fb"
UUID_KEY_WRITE = "0000fff3-0000-1000-8000-00805f9b34fb"


@dataclass
class HistoryReading:
    date: datetime
    voltage: float
    unused: int
    min_crank_voltage: float
    type: int


class PacketType(enum.Enum):
    VoltageReading = b"\xf5"
    HistoryCount = b"\xe7"
    StartHistory = b"\xff\xff\xfe"
    EndHistory = b"\xff\xfe\xfe"


class BM2Client:
    def __init__(self, mac: str):
        self._mac = mac

        self._stop = True

        self._client: Optional[BleakClient] = None
        self._connected_event = asyncio.Condition()
        self._mainloop_task: Optional[Task[Any]] = None

        self._request_sem = asyncio.Semaphore()

        self._future_voltage_reading: Optional[asyncio.Future[float]] = None

        self._is_receiving_history = False
        self._history_data = b""
        self._future_history_readings: Optional[asyncio.Future[List[HistoryReading]]] = None

    def start(self) -> None:
        if self._client is not None:
            return
        self._stop = False
        self._mainloop_task = asyncio.create_task(self._mainloop())

    def stop(self) -> None:
        self._stop = True
        if self._client is not None:
            asyncio.create_task(self._client.disconnect())
        if self._mainloop_task is not None:
            self._mainloop_task.cancel()
        self._client = None

    async def wait_for_connected(self) -> None:
        if self._stop:
            raise NotConnectedError()

        async with self._connected_event:
            await self._connected_event.wait_for(lambda: self._client is not None)

    async def get_history(self) -> List[HistoryReading]:
        async with self._request_sem:
            if self._stop:
                raise NotConnectedError()

            f = asyncio.Future[List[HistoryReading]]()
            self._future_history_readings = f
            await self._send([0xe7, 1])
            return await asyncio.wait_for(f, 5)

    async def get_voltage(self) -> float:
        async with self._request_sem:
            if self._stop:
                raise NotConnectedError()

            f = asyncio.Future[float]()
            self._future_voltage_reading = f
            return await asyncio.wait_for(f, 60)

    async def _send(self, data: List[int]) -> None:
        await self.wait_for_connected()

        assert self._client is not None

        await self._client.write_gatt_char(UUID_KEY_WRITE, encrypt(bytes(data)))

    async def _mainloop(self) -> None:
        while not self._stop:
            try:
                async with BleakClient(self._mac) as client:
                    logger.info(f"Connected")

                    await client.start_notify(UUID_KEY_READ, self._notification_handler)
                    self._client = client

                    while True:
                        if not client.is_connected:
                            break

                        async with self._connected_event:
                            self._connected_event.notify_all()

                        await asyncio.sleep(1)

            except bleak.exc.BleakError as e:
                if "was not found" in e.args[0]:
                    logger.info("Performing forceful device disconnection")
                    subprocess.run("bluetoothctl", input=f"disconnect {self._mac}".encode("ascii"), stdout=subprocess.DEVNULL)
                elif "org.freedesktop.DBus.Error.NoReply" in e.args[0]:
                    pass
                else:
                    logger.error(e)
            except OSError as e:
                logger.error(e)
            finally:
                self._client = None
                self._fulfill_history_reading_future(exception=NotConnectedError())

                await asyncio.sleep(1)

    def _notification_handler(self, _: Any, encrypted_data: bytearray) -> None:
        decrypted_data = decrypt(encrypted_data)

        def is_of_type(packet_type: PacketType) -> bool:
            return decrypted_data[0:len(packet_type.value)] == packet_type.value

        if is_of_type(PacketType.VoltageReading):
            voltage = (struct.unpack(">H", decrypted_data[1:1 + 2])[0] >> 4) / 100
            self._fulfill_voltage_reading_future(voltage)

        elif is_of_type(PacketType.HistoryCount):
            history_size = decode_3bytes(decrypted_data[1:1 + 3])

            if history_size == 0:
                self._fulfill_history_reading_future([])
            else:
                async def fn() -> None:
                    await asyncio.sleep(1)  # required, otherwise BM2 ignores the following packet
                    await self._send([0xe3, 0, 0, *struct.pack(">L", history_size)])

                asyncio.create_task(fn())

        elif is_of_type(PacketType.StartHistory):
            self._is_receiving_history = True
            self._history_data = b""

        elif self._is_receiving_history:
            if is_of_type(PacketType.EndHistory):
                self._is_receiving_history = False
                history_data_size = decode_3bytes(decrypted_data[3:3 + 3]) - 9

                history_data = self._history_data[0:history_data_size]
                history_items_count = len(history_data) // 4
                history_items_bytes = [history_data[i:i + 4] for i in range(0, len(history_data), 4)]

                def process_history_item(i: int, x: bytes) -> HistoryReading:
                    date = datetime.now().replace(microsecond=0, second=0) - timedelta(minutes=(history_items_count - 1 - i) * 2)
                    values = decode_nibbles(x, "xxxkyyyp")
                    return HistoryReading(date=date,
                                          voltage=values[0] / 100,
                                          unused=values[1],
                                          min_crank_voltage=values[2] / 100,
                                          type=values[3])

                history_items = [process_history_item(i, x) for i, x in enumerate(history_items_bytes)]

                self._fulfill_history_reading_future(history_items)
            else:
                self._history_data += decrypted_data

        else:
            logger.info(f"unknown packet: {binascii.hexlify(decrypted_data).decode('ascii')}")

    def _fulfill_voltage_reading_future(self, result: Optional[float] = None, exception: Optional[Exception] = None) -> None:
        f = self._future_voltage_reading
        self._future_voltage_reading = None

        if f is not None and not f.done():
            if result is not None:
                f.set_result(result)
            elif exception is not None:
                f.set_exception(exception)

    def _fulfill_history_reading_future(self, result: Optional[List[HistoryReading]] = None, exception: Optional[Exception] = None) -> None:
        f = self._future_history_readings
        self._future_history_readings = None

        if f is not None and not f.done():
            if result is not None:
                f.set_result(result)
            elif exception is not None:
                f.set_exception(exception)


class NotConnectedError(Exception):
    pass


__all__ = [
    "BM2Client",
    "NotConnectedError",
]
