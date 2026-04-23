"""闲鱼接入工具。"""

from __future__ import annotations

import base64
import hashlib
import json
import random
import struct
import time
from typing import Any


def parse_cookies(cookies_str: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for cookie in cookies_str.split(";"):
        if "=" not in cookie:
            continue
        key, value = cookie.strip().split("=", 1)
        cookies[key] = value
    return cookies


def cookies_to_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def generate_mid() -> str:
    return f"{int(1000 * random.random())}{int(time.time() * 1000)} 0"


def generate_uuid() -> str:
    return f"-{int(time.time() * 1000)}1"


def generate_device_id(user_id: str) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    result: list[str] = []
    for index in range(36):
        if index in [8, 13, 18, 23]:
            result.append("-")
        elif index == 14:
            result.append("4")
        else:
            rand_val = int(16 * random.random())
            if index == 19:
                rand_val = (rand_val & 0x3) | 0x8
            result.append(chars[rand_val])
    return "".join(result) + "-" + user_id


def generate_sign(timestamp: str, token: str, data: str) -> str:
    app_key = "34839810"
    value = f"{token}&{timestamp}&{app_key}&{data}"
    return hashlib.md5(value.encode("utf-8")).hexdigest()


class MessagePackDecoder:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0
        self.length = len(data)

    def read_byte(self) -> int:
        if self.pos >= self.length:
            raise ValueError("unexpected end of data")
        byte = self.data[self.pos]
        self.pos += 1
        return byte

    def read_bytes(self, count: int) -> bytes:
        if self.pos + count > self.length:
            raise ValueError("unexpected end of data")
        result = self.data[self.pos : self.pos + count]
        self.pos += count
        return result

    def decode_value(self) -> Any:
        fmt = self.read_byte()
        if fmt <= 0x7F:
            return fmt
        if 0x80 <= fmt <= 0x8F:
            return {self.decode_value(): self.decode_value() for _ in range(fmt & 0x0F)}
        if 0x90 <= fmt <= 0x9F:
            return [self.decode_value() for _ in range(fmt & 0x0F)]
        if 0xA0 <= fmt <= 0xBF:
            return self.read_bytes(fmt & 0x1F).decode("utf-8")
        if fmt == 0xC0:
            return None
        if fmt == 0xC2:
            return False
        if fmt == 0xC3:
            return True
        if fmt == 0xC4:
            return self.read_bytes(self.read_byte())
        if fmt == 0xC5:
            return self.read_bytes(struct.unpack(">H", self.read_bytes(2))[0])
        if fmt == 0xC6:
            return self.read_bytes(struct.unpack(">I", self.read_bytes(4))[0])
        if fmt == 0xCA:
            return struct.unpack(">f", self.read_bytes(4))[0]
        if fmt == 0xCB:
            return struct.unpack(">d", self.read_bytes(8))[0]
        if fmt == 0xCC:
            return self.read_byte()
        if fmt == 0xCD:
            return struct.unpack(">H", self.read_bytes(2))[0]
        if fmt == 0xCE:
            return struct.unpack(">I", self.read_bytes(4))[0]
        if fmt == 0xCF:
            return struct.unpack(">Q", self.read_bytes(8))[0]
        if fmt == 0xD0:
            return struct.unpack(">b", self.read_bytes(1))[0]
        if fmt == 0xD1:
            return struct.unpack(">h", self.read_bytes(2))[0]
        if fmt == 0xD2:
            return struct.unpack(">i", self.read_bytes(4))[0]
        if fmt == 0xD3:
            return struct.unpack(">q", self.read_bytes(8))[0]
        if fmt == 0xD9:
            return self.read_bytes(self.read_byte()).decode("utf-8")
        if fmt == 0xDA:
            return self.read_bytes(struct.unpack(">H", self.read_bytes(2))[0]).decode("utf-8")
        if fmt == 0xDB:
            return self.read_bytes(struct.unpack(">I", self.read_bytes(4))[0]).decode("utf-8")
        if fmt == 0xDC:
            return [self.decode_value() for _ in range(struct.unpack(">H", self.read_bytes(2))[0])]
        if fmt == 0xDD:
            return [self.decode_value() for _ in range(struct.unpack(">I", self.read_bytes(4))[0])]
        if fmt == 0xDE:
            size = struct.unpack(">H", self.read_bytes(2))[0]
            return {self.decode_value(): self.decode_value() for _ in range(size)}
        if fmt == 0xDF:
            size = struct.unpack(">I", self.read_bytes(4))[0]
            return {self.decode_value(): self.decode_value() for _ in range(size)}
        if fmt >= 0xE0:
            return fmt - 256
        raise ValueError(f"unsupported message pack format: {fmt}")


def decrypt_message(data: str) -> dict[str, Any]:
    cleaned = "".join(ch for ch in data if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    while len(cleaned) % 4 != 0:
        cleaned += "="
    decoded = base64.b64decode(cleaned)
    try:
        decoder = MessagePackDecoder(decoded)
        result = decoder.decode_value()
        if isinstance(result, dict):
            return result
        return {"raw": result}
    except Exception:
        try:
            text = decoded.decode("utf-8")
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {"raw": parsed}
        except Exception:
            return {"raw_base64": cleaned}


def to_text_payload(text: str) -> str:
    payload = {"contentType": 1, "text": {"text": text}}
    return base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("utf-8")
