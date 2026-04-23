import struct


def detect_image_dimensions(mime_type: str, content: bytes) -> tuple[int | None, int | None]:
    if mime_type == "image/png":
        return _detect_png_dimensions(content)
    if mime_type == "image/jpeg":
        return _detect_jpeg_dimensions(content)
    if mime_type == "image/webp":
        return _detect_webp_dimensions(content)
    return None, None


def _detect_png_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 24 or not content.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, None
    width, height = struct.unpack(">II", content[16:24])
    return width, height


def _detect_jpeg_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 4 or not content.startswith(b"\xff\xd8"):
        return None, None

    index = 2
    while index + 9 < len(content):
        if content[index] != 0xFF:
            index += 1
            continue

        marker = content[index + 1]
        index += 2

        while marker == 0xFF and index < len(content):
            marker = content[index]
            index += 1

        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(content):
            return None, None

        segment_length = int.from_bytes(content[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(content):
            return None, None

        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height = int.from_bytes(content[index + 3:index + 5], "big")
            width = int.from_bytes(content[index + 5:index + 7], "big")
            return width, height

        index += segment_length

    return None, None


def _detect_webp_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 30 or content[:4] != b"RIFF" or content[8:12] != b"WEBP":
        return None, None

    chunk_type = content[12:16]
    if chunk_type == b"VP8X" and len(content) >= 30:
        width = int.from_bytes(content[24:27], "little") + 1
        height = int.from_bytes(content[27:30], "little") + 1
        return width, height
    if chunk_type == b"VP8 " and len(content) >= 30:
        width = int.from_bytes(content[26:28], "little") & 0x3FFF
        height = int.from_bytes(content[28:30], "little") & 0x3FFF
        return width, height
    if chunk_type == b"VP8L" and len(content) >= 25:
        packed = int.from_bytes(content[21:25], "little")
        width = (packed & 0x3FFF) + 1
        height = ((packed >> 14) & 0x3FFF) + 1
        return width, height

    return None, None
