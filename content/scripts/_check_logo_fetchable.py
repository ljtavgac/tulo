"""One-off, read-only: confirms https://tulo.io/brand/tulo-light.png is
publicly fetchable and reports its real pixel dimensions, so Organization
JSON-LD's `logo` field can be trusted to meet Google's >=112x112 minimum
before it ships.

Usage: python3 content/scripts/_check_logo_fetchable.py
"""

import struct
import urllib.request

URL = "https://tulo.io/brand/tulo-light.png"


def png_dimensions(data: bytes) -> tuple[int, int]:
    # PNG: 8-byte signature, then IHDR chunk: 4-byte length, 4-byte "IHDR",
    # then width (4 bytes) + height (4 bytes), all big-endian.
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG (bad signature)")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (logo-check)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.status
        content_type = resp.headers.get("Content-Type")
        data = resp.read()

    print(f"URL: {URL}")
    print(f"HTTP status: {status}")
    print(f"Content-Type: {content_type}")
    print(f"Bytes fetched: {len(data)}")

    width, height = png_dimensions(data)
    print(f"Real pixel dimensions: {width}x{height}")
    print(f"Meets Google's >=112x112 minimum: {width >= 112 and height >= 112}")


if __name__ == "__main__":
    main()
