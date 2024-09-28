from abc import abstractmethod
from typing import Callable, Optional


class BaseTransport:
    def __init__(self) -> None:
        self._on_data_handler: Optional[Callable[[bytes], None]] = None

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    async def write(self, data: bytes) -> None:
        pass

    def set_on_data_handler(self, on_data: Callable[[bytes], None]) -> None:
        self._on_data_handler = on_data

    def _notify_data(self, data: bytes) -> None:
        if self._on_data_handler is not None:
            self._on_data_handler(data)


__all__ = [
    "BaseTransport",
]
