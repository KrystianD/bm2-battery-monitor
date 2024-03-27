from typing import Any, cast, Union

from Crypto.Cipher import AES

BM2_ENCRYPTION_KEY = b"\x6c\x65\x61\x67\x65\x6e\x64\xff\xfe\x31\x38\x38\x32\x34\x36\x36"

AesBlockSize = 16


def create_aes() -> Any:
    return AES.new(BM2_ENCRYPTION_KEY, AES.MODE_CBC, bytes([0] * AesBlockSize))


def pad_to_block(x: bytes) -> bytes:
    required_size = (len(x) + (AesBlockSize - 1)) // AesBlockSize * AesBlockSize
    return x.ljust(required_size, b"\x00")


def encrypt(data: bytes) -> bytes:
    return cast(bytes, create_aes().encrypt(pad_to_block(data)))


def decrypt(encrypted_data: Union[bytes, bytearray]) -> bytes:
    return cast(bytes, create_aes().decrypt(bytes(encrypted_data)))
