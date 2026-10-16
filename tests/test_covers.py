import base64
import zlib

from app.routes.covers import decode_image

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


def test_raw_image():
    assert decode_image(PNG) == (PNG, "image/png")


def test_base64_image():
    assert decode_image(base64.b64encode(JPEG)) == (JPEG, "image/jpeg")


def test_base64_with_line_breaks():
    encoded = base64.encodebytes(PNG * 10)
    assert decode_image(encoded) == (PNG * 10, "image/png")


def test_qcompress_image():
    wrapped = len(JPEG).to_bytes(4, "big") + zlib.compress(JPEG)
    assert decode_image(wrapped) == (JPEG, "image/jpeg")


def test_unrecognised_data():
    assert decode_image(b"not an image") is None
