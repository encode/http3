import subprocess
import sys
import typing

import pytest

import httpx


def test_get(server):
    response = httpx.get(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


def test_post(server):
    response = httpx.post(server.url, content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_post_byte_iterator(server):
    def data() -> typing.Iterator[bytes]:
        yield b"Hello"
        yield b", "
        yield b"world!"

    response = httpx.post(server.url, content=data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_post_byte_stream(server):
    class Data(httpx.SyncByteStream):
        def __iter__(self):
            yield b"Hello"
            yield b", "
            yield b"world!"

    response = httpx.post(server.url, content=Data())
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_options(server):
    response = httpx.options(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_head(server):
    response = httpx.head(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_put(server):
    response = httpx.put(server.url, content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_patch(server):
    response = httpx.patch(server.url, content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_delete(server):
    response = httpx.delete(server.url)
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


def test_stream(server):
    with httpx.stream("GET", server.url) as response:
        response.read()

    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"


def test_get_invalid_url():
    with pytest.raises(httpx.UnsupportedProtocol):
        httpx.get("invalid://example.org")


# check that httpcore isn't imported until we do a request
def test_httpcore_lazy_loading(server):
    subprocess.check_call(
        [
            sys.executable,
            "-c",
            "import httpx,sys;assert 'httpcore' not in sys.modules;"
            + f"_response = httpx.get('{server.url}');"
            + "assert 'httpcore' in sys.modules",
        ]
    )
