import binascii
import itertools
import struct
from typing import List, cast


# B1 B2 B3 -> 0x00B1B2B3 (big endian int)
def decode_3bytes(x: bytes) -> int:
    assert len(x) >= 3
    return cast(int, struct.unpack(">L", bytes([0, *x]))[0])


def decode_nibbles(x: bytes, fmt: str) -> List[int]:
    """
    x: 4d411111 fmt: xxxkyyyp

    xxx = 0x4d4 = 1236
    k   = 0x1   = 1
    yyy = 0x111 = 273
    p   = 0x1   = 1
    """
    hex_str = binascii.hexlify(x)
    letter_groups = [(x[0], len(list(x[1]))) for x in itertools.groupby(fmt)]
    idx = 0
    values = []
    for letter, letters_count in letter_groups:
        hex_str_part = hex_str[idx:idx + letters_count]
        idx += letters_count

        values.append(sum((int(chr(x), 16) << (4 * i)) for i, x in enumerate(reversed(hex_str_part))))
    return values
