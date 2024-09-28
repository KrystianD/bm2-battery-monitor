import asyncio
import logging
import subprocess
import weakref
from typing import Optional, Any

from bleak import BleakClient

from bm2.constants import READ_CHAR_UUID, WRITE_CHAR_UUID
from bm2.transports.BaseTransport import BaseTransport

logger = logging.getLogger("TransportBleak")


async def run_bluetoothctl(command: str) -> None:
    subprocess.run("bluetoothctl", input=command.encode("ascii"), stdout=subprocess.DEVNULL)
    await asyncio.sleep(1)


class TransportBleak(BaseTransport):
    def __init__(self, client: BleakClient):
        super().__init__()
        self._client = client

        self._disconnect_task: Optional[asyncio.Task[Any]] = None

    def close(self) -> None:
        if self._disconnect_task is not None:
            return

        self._disconnect_task = asyncio.create_task(self._client.disconnect())

    async def write(self, data: bytes) -> None:
        await self._client.write_gatt_char(WRITE_CHAR_UUID, data)

    @staticmethod
    async def connect(mac_addr: str) -> 'TransportBleak':
        client = BleakClient(mac_addr)

        logger.debug("restarting bluetooth")
        await run_bluetoothctl(f"disconnect {mac_addr}")
        await run_bluetoothctl(f"power on")

        logger.debug("connecting to client")
        await client.connect()

        transport = TransportBleak(client)

        weak_handler = weakref.WeakMethod(transport._notify_data)

        def on_bluetooth_gatt_notify(_: Any, b: bytearray) -> None:
            weak_handler()(bytes(b))  # type: ignore

        await client.start_notify(READ_CHAR_UUID, on_bluetooth_gatt_notify)

        return transport


__all__ = [
    "TransportBleak",
]
