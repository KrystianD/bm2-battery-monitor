import asyncio
import binascii
import logging
import weakref
from typing import Optional, Callable, Any

import aioesphomeapi

from bm2.constants import WRITE_CHAR_UUID, READ_CHAR_UUID
from bm2.transports.BaseTransport import BaseTransport

logger = logging.getLogger("TransportESPHomeBluetoothProxy")


def mac_to_int(mac_str: str) -> int:
    return int.from_bytes(binascii.unhexlify(mac_str.replace(":", "")), 'big')


class TransportESPHomeBluetoothProxy(BaseTransport):
    def __init__(self, client: aioesphomeapi.APIClient, mac_addr_int: int, unsub: Callable[..., Any], write_char_handle: int) -> None:
        super().__init__()
        self._client = client
        self._mac_addr_int = mac_addr_int
        self._unsub = unsub
        self._write_char_handle = write_char_handle

        self._disconnect_task: Optional[asyncio.Task[Any]] = None

    def close(self) -> None:
        if self._disconnect_task is not None:
            return

        self._unsub()
        self._disconnect_task = asyncio.create_task(self._client.disconnect())

    async def write(self, data: bytes) -> None:
        await self._client.bluetooth_gatt_write(self._mac_addr_int, self._write_char_handle, data, response=False)
        await asyncio.sleep(1)

    @staticmethod
    async def connect(esphome_host: str, esphome_port: int, esphome_password: str, mac_addr: str) -> 'TransportESPHomeBluetoothProxy':
        api = aioesphomeapi.APIClient(esphome_host, esphome_port, esphome_password)
        await api.connect(login=True)

        mac_addr_int = mac_to_int(mac_addr)

        unsub = api.subscribe_bluetooth_le_advertisements(lambda _: None)

        await api.bluetooth_device_connect(mac_addr_int, lambda _1, _2, _3: None, address_type=0)

        services_resp = await api.bluetooth_gatt_get_services(mac_addr_int)
        uuid_to_handle = {y.uuid: y.handle for x in services_resp.services for y in x.characteristics}

        read_char_handle = uuid_to_handle[READ_CHAR_UUID]
        write_char_handle = uuid_to_handle[WRITE_CHAR_UUID]

        transport = TransportESPHomeBluetoothProxy(api, mac_addr_int, unsub, write_char_handle)

        weak_handler = weakref.WeakMethod(transport._notify_data)

        def on_bluetooth_gatt_notify(_: int, b: bytearray) -> None:
            weak_handler()(bytes(b))  # type: ignore

        await api.bluetooth_gatt_start_notify(mac_addr_int, read_char_handle, on_bluetooth_gatt_notify)
        await asyncio.sleep(1)

        return transport


__all__ = [
    "TransportESPHomeBluetoothProxy",
]
