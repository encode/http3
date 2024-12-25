from __future__ import annotations

import io
import tempfile
import typing

import anyio
import pytest
import trio

import httpx


def echo_request_content(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=request.content)


@pytest.mark.parametrize(("value,output"), (("abc", b"abc"), (b"abc", b"abc")))
def test_multipart(value, output):
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    # Test with a single-value 'data' argument, and a plain file 'files' argument.
    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    boundary_bytes = boundary.encode("ascii")

    assert response.status_code == 200
    assert response.content == b"".join(
        [
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="text"\r\n',
            b"\r\n",
            b"abc\r\n",
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--" + boundary_bytes + b"--\r\n",
        ]
    )


async def test_async_multipart_streaming(tmp_path, server, anyio_backend):
    content = b"\n".join([b"a" * io.DEFAULT_BUFFER_SIZE] * 3)
    to_upload = tmp_path / "test.txt"
    to_upload.write_bytes(content)
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    opener: typing.Any
    text_opener: typing.Any
    empty_opener: typing.Any
    if anyio_backend == "trio":
        opener = trio.open_file(to_upload, "b+r")
        text_opener = trio.open_file(to_upload, "t+r")
        empty_opener = trio.open_file(empty_file, "b+r")
    else:
        opener = anyio.open_file(to_upload, "b+r")
        text_opener = anyio.open_file(to_upload, "t+r")
        empty_opener = anyio.open_file(empty_file, "b+r")
    url = server.url.copy_with(path="/echo_body")
    async with await opener as fp, httpx.AsyncClient() as client:
        files = {"file": fp}
        response = await client.post(url, files=files)
        boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
        boundary_bytes = boundary.encode("ascii")

        assert response.status_code == 200
        assert response.content == b"".join(
            [
                b"--" + boundary_bytes + b"\r\n",
                b'Content-Disposition: form-data; name="file";'
                b' filename="test.txt"\r\n',
                b"Content-Type: text/plain\r\n",
                b"\r\n",
                content,
                b"\r\n",
                b"--" + boundary_bytes + b"--\r\n",
            ]
        )

        with httpx.Client() as sync_client:
            with pytest.raises(TypeError, match="AsyncIterable is not supported"):
                sync_client.post(url, files=files)

    async with await text_opener as fp, httpx.AsyncClient() as client:
        files = {"file": fp}
        with pytest.raises(
            TypeError,
            match="Multipart file uploads must be opened in binary mode",
        ):
            await client.post(url, files=files)

    async with await empty_opener as fp, httpx.AsyncClient() as client:
        files = {"file": fp}
        await client.post(url, files=files)


@pytest.mark.parametrize(
    "header",
    [
        "multipart/form-data; boundary=+++; charset=utf-8",
        "multipart/form-data; charset=utf-8; boundary=+++",
        "multipart/form-data; boundary=+++",
        "multipart/form-data; boundary=+++ ;",
        'multipart/form-data; boundary="+++"; charset=utf-8',
        'multipart/form-data; charset=utf-8; boundary="+++"',
        'multipart/form-data; boundary="+++"',
        'multipart/form-data; boundary="+++" ;',
    ],
)
def test_multipart_explicit_boundary(header: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    files = {"file": io.BytesIO(b"<file content>")}
    headers = {"content-type": header}
    response = client.post("http://127.0.0.1:8000/", files=files, headers=headers)
    boundary_bytes = b"+++"

    assert response.status_code == 200
    assert response.request.headers["Content-Type"] == header
    assert response.content == b"".join(
        [
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--" + boundary_bytes + b"--\r\n",
        ]
    )


@pytest.mark.parametrize(
    "header",
    [
        "multipart/form-data; charset=utf-8",
        "multipart/form-data; charset=utf-8; ",
    ],
)
def test_multipart_header_without_boundary(header: str) -> None:
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    files = {"file": io.BytesIO(b"<file content>")}
    headers = {"content-type": header}
    response = client.post("http://127.0.0.1:8000/", files=files, headers=headers)

    assert response.status_code == 200
    assert response.request.headers["Content-Type"] == header


@pytest.mark.parametrize(("key"), (b"abc", 1, 2.3, None))
def test_multipart_invalid_key(key):
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    data = {key: "abc"}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        client.post(
            "http://127.0.0.1:8000/",
            data=data,
            files=files,
        )
    assert "Invalid type for name" in str(e.value)
    assert repr(key) in str(e.value)


@pytest.mark.parametrize(("value"), (object(), {"key": "value"}))
def test_multipart_invalid_value(value):
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    data = {"text": value}
    files = {"file": io.BytesIO(b"<file content>")}
    with pytest.raises(TypeError) as e:
        client.post("http://127.0.0.1:8000/", data=data, files=files)
    assert "Invalid type for value" in str(e.value)


def test_multipart_file_tuple():
    client = httpx.Client(transport=httpx.MockTransport(echo_request_content))

    # Test with a list of values 'data' argument,
    #     and a tuple style 'files' argument.
    data = {"text": ["abc"]}
    files = {"file": ("name.txt", io.BytesIO(b"<file content>"))}
    response = client.post("http://127.0.0.1:8000/", data=data, files=files)
    boundary = response.request.headers["Content-Type"].split("boundary=")[-1]
    boundary_bytes = boundary.encode("ascii")

    assert response.status_code == 200
    assert response.content == b"".join(
        [
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="text"\r\n',
            b"\r\n",
            b"abc\r\n",
            b"--" + boundary_bytes + b"\r\n",
            b'Content-Disposition: form-data; name="file"; filename="name.txt"\r\n',
            b"Content-Type: text/plain\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--" + boundary_bytes + b"--\r\n",
        ]
    )


@pytest.mark.parametrize("file_content_type", [None, "text/plain"])
def test_multipart_file_tuple_headers(file_content_type: str | None) -> None:
    file_name = "test.txt"
    file_content = io.BytesIO(b"<file content>")
    file_headers = {"Expires": "0"}

    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": (file_name, file_content, file_content_type, file_headers)}

    request = httpx.Request("POST", url, headers=headers, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        f'--BOUNDARY\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{file_name}"\r\nExpires: 0\r\nContent-Type: '
        f"text/plain\r\n\r\n<file content>\r\n--BOUNDARY--\r\n"
        "".encode("ascii")
    )


def test_multipart_headers_include_content_type() -> None:
    """
    Content-Type from 4th tuple parameter (headers) should
    override the 3rd parameter (content_type)
    """
    file_name = "test.txt"
    file_content = io.BytesIO(b"<file content>")
    file_content_type = "text/plain"
    file_headers = {"Content-Type": "image/png"}

    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": (file_name, file_content, file_content_type, file_headers)}

    request = httpx.Request("POST", url, headers=headers, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        f'--BOUNDARY\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{file_name}"\r\nContent-Type: '
        f"image/png\r\n\r\n<file content>\r\n--BOUNDARY--\r\n"
        "".encode("ascii")
    )


def test_multipart_encode(tmp_path: typing.Any) -> None:
    path = str(tmp_path / "name.txt")
    with open(path, "wb") as f:
        f.write(b"<file content>")

    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    data = {
        "a": "1",
        "b": b"C",
        "c": ["11", "22", "33"],
        "d": "",
        "e": True,
        "f": "",
    }
    with open(path, "rb") as input_file:
        files = {"file": ("name.txt", input_file)}

        request = httpx.Request("POST", url, headers=headers, data=data, files=files)
        request.read()

        assert request.headers == {
            "Host": "www.example.com",
            "Content-Type": "multipart/form-data; boundary=BOUNDARY",
            "Content-Length": str(len(request.content)),
        }
        assert request.content == (
            '--BOUNDARY\r\nContent-Disposition: form-data; name="a"\r\n\r\n1\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="b"\r\n\r\nC\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="c"\r\n\r\n11\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="c"\r\n\r\n22\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="c"\r\n\r\n33\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="d"\r\n\r\n\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="e"\r\n\r\ntrue\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="f"\r\n\r\n\r\n'
            '--BOUNDARY\r\nContent-Disposition: form-data; name="file";'
            ' filename="name.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n<file content>\r\n"
            "--BOUNDARY--\r\n"
            "".encode("ascii")
        )


def test_multipart_encode_unicode_file_contents() -> None:
    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": ("name.txt", b"<bytes content>")}

    request = httpx.Request("POST", url, headers=headers, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        b'--BOUNDARY\r\nContent-Disposition: form-data; name="file";'
        b' filename="name.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\n<bytes content>\r\n"
        b"--BOUNDARY--\r\n"
    )


def test_multipart_encode_files_allows_filenames_as_none() -> None:
    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": (None, io.BytesIO(b"<file content>"))}

    request = httpx.Request("POST", url, headers=headers, data={}, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        '--BOUNDARY\r\nContent-Disposition: form-data; name="file"\r\n\r\n'
        "<file content>\r\n--BOUNDARY--\r\n"
        "".encode("ascii")
    )


@pytest.mark.parametrize(
    "file_name,expected_content_type",
    [
        ("example.json", "application/json"),
        ("example.txt", "text/plain"),
        ("no-extension", "application/octet-stream"),
    ],
)
def test_multipart_encode_files_guesses_correct_content_type(
    file_name: str, expected_content_type: str
) -> None:
    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": (file_name, io.BytesIO(b"<file content>"))}

    request = httpx.Request("POST", url, headers=headers, data={}, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        f'--BOUNDARY\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{file_name}"\r\nContent-Type: '
        f"{expected_content_type}\r\n\r\n<file content>\r\n--BOUNDARY--\r\n"
        "".encode("ascii")
    )


def test_multipart_encode_files_allows_bytes_content() -> None:
    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": ("test.txt", b"<bytes content>", "text/plain")}

    request = httpx.Request("POST", url, headers=headers, data={}, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        '--BOUNDARY\r\nContent-Disposition: form-data; name="file"; '
        'filename="test.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n<bytes content>\r\n"
        "--BOUNDARY--\r\n"
        "".encode("ascii")
    )


def test_multipart_encode_files_allows_str_content() -> None:
    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    files = {"file": ("test.txt", "<str content>", "text/plain")}

    request = httpx.Request("POST", url, headers=headers, data={}, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Content-Length": str(len(request.content)),
    }
    assert request.content == (
        '--BOUNDARY\r\nContent-Disposition: form-data; name="file"; '
        'filename="test.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n<str content>\r\n"
        "--BOUNDARY--\r\n"
        "".encode("ascii")
    )


def test_multipart_encode_files_raises_exception_with_StringIO_content() -> None:
    url = "https://www.example.com"
    files = {"file": ("test.txt", io.StringIO("content"), "text/plain")}
    with pytest.raises(TypeError):
        httpx.Request("POST", url, data={}, files=files)  # type: ignore


def test_multipart_encode_files_raises_exception_with_text_mode_file() -> None:
    url = "https://www.example.com"
    with tempfile.TemporaryFile(mode="w") as upload:
        files = {"file": ("test.txt", upload, "text/plain")}
        with pytest.raises(TypeError):
            httpx.Request("POST", url, data={}, files=files)  # type: ignore


def test_multipart_encode_non_seekable_filelike() -> None:
    """
    Test that special readable but non-seekable filelike objects are supported.
    In this case uploads with use 'Transfer-Encoding: chunked', instead of
    a 'Content-Length' header.
    """

    class IteratorIO(io.IOBase):
        def __init__(self, iterator: typing.Iterator[bytes]) -> None:
            self._iterator = iterator

        def read(self, *args: typing.Any) -> bytes:
            return b"".join(self._iterator)

    def data() -> typing.Iterator[bytes]:
        yield b"Hello"
        yield b"World"

    url = "https://www.example.com/"
    headers = {"Content-Type": "multipart/form-data; boundary=BOUNDARY"}
    fileobj: typing.Any = IteratorIO(data())
    files = {"file": fileobj}

    request = httpx.Request("POST", url, headers=headers, files=files)
    request.read()

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Type": "multipart/form-data; boundary=BOUNDARY",
        "Transfer-Encoding": "chunked",
    }
    assert request.content == (
        b"--BOUNDARY\r\n"
        b'Content-Disposition: form-data; name="file"; filename="upload"\r\n'
        b"Content-Type: application/octet-stream\r\n"
        b"\r\n"
        b"HelloWorld\r\n"
        b"--BOUNDARY--\r\n"
    )


def test_multipart_rewinds_files():
    with tempfile.TemporaryFile() as upload:
        upload.write(b"Hello, world!")

        transport = httpx.MockTransport(echo_request_content)
        client = httpx.Client(transport=transport)

        files = {"file": upload}
        response = client.post("http://127.0.0.1:8000/", files=files)
        assert response.status_code == 200
        assert b"\r\nHello, world!\r\n" in response.content

        # POSTing the same file instance a second time should have the same content.
        files = {"file": upload}
        response = client.post("http://127.0.0.1:8000/", files=files)
        assert response.status_code == 200
        assert b"\r\nHello, world!\r\n" in response.content


class TestHeaderParamHTML5Formatting:
    def test_unicode(self):
        filename = "n\u00e4me"
        expected = b'filename="n\xc3\xa4me"'
        files = {"upload": (filename, b"<file content>")}
        request = httpx.Request("GET", "https://www.example.com", files=files)
        assert expected in request.read()

    def test_ascii(self):
        filename = "name"
        expected = b'filename="name"'
        files = {"upload": (filename, b"<file content>")}
        request = httpx.Request("GET", "https://www.example.com", files=files)
        assert expected in request.read()

    def test_unicode_escape(self):
        filename = "hello\\world\u0022"
        expected = b'filename="hello\\\\world%22"'
        files = {"upload": (filename, b"<file content>")}
        request = httpx.Request("GET", "https://www.example.com", files=files)
        assert expected in request.read()

    def test_unicode_with_control_character(self):
        filename = "hello\x1a\x1b\x1c"
        expected = b'filename="hello%1A\x1b%1C"'
        files = {"upload": (filename, b"<file content>")}
        request = httpx.Request("GET", "https://www.example.com", files=files)
        assert expected in request.read()
