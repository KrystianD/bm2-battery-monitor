import asyncio
import binascii
import enum
import logging
import struct
import weakref
from asyncio import Task
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import List, Optional, Any

from bm2.bit_utils import decode_3bytes, decode_nibbles
from bm2.encryption import encrypt, decrypt
from bm2.transports.BaseTransport import BaseTransport

logger = logging.getLogger("bm2_client")


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
    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport

        self._stop = True

        self._mainloop_task: Optional[Task[Any]] = None

        self._request_sem = asyncio.Semaphore()

        self._future_voltage_reading: Optional[asyncio.Future[float]] = None

        self._is_receiving_history = False
        self._history_data = b""
        self._future_history_readings: Optional[asyncio.Future[List[HistoryReading]]] = None

        self_ref = weakref.WeakMethod(self._notification_handler)
        self._transport.set_on_data_handler(lambda x: self_ref()(x))  # type: ignore

    def close(self) -> None:
        self._transport.close()

    async def get_history(self) -> List[HistoryReading]:
        async with self._request_sem:
            f = asyncio.Future[List[HistoryReading]]()
            self._future_history_readings = f
            await self._send([0xe7, 1])
            return await asyncio.wait_for(f, 5)

    async def get_voltage(self) -> float:
        async with self._request_sem:
            f = asyncio.Future[float]()
            self._future_voltage_reading = f
            return await asyncio.wait_for(f, 5)

    async def _send(self, data: List[int]) -> None:
        await self._transport.write(encrypt(bytes(data)))

    def _notification_handler(self, encrypted_data: bytes) -> None:
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
