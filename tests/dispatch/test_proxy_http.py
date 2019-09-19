import pytest

import httpx

from .utils import MockRawSocketBackend


async def test_proxy_tunnel_success(backend):
    raw_io = MockRawSocketBackend(
        data_to_send=(
            [
                b"HTTP/1.1 200 OK\r\n"
                b"Date: Sun, 10 Oct 2010 23:26:07 GMT\r\n"
                b"Server: proxy-server\r\n"
                b"\r\n",
                b"HTTP/1.1 404 Not Found\r\n"
                b"Date: Sun, 10 Oct 2010 23:26:07 GMT\r\n"
                b"Server: origin-server\r\n"
                b"\r\n",
            ]
        ),
        backend=backend,
    )
    async with httpx.HTTPProxy(
        proxy_url="http://127.0.0.1:8000",
        backend=raw_io,
        proxy_mode=httpx.HTTPProxyMode.TUNNEL_ONLY,
    ) as proxy:
        response = await proxy.request("GET", f"http://example.com")

        assert response.status_code == 404
        assert response.headers["Server"] == "origin-server"

        assert response.request.method == "GET"
        assert response.request.url == "http://example.com"
        assert response.request.headers["Host"] == "example.com"

    recv = raw_io.received_data
    assert len(recv) == 3
    assert recv[0] == b"--- CONNECT(127.0.0.1, 8000) ---"
    assert recv[1].startswith(
        b"CONNECT example.com:80 HTTP/1.1\r\nhost: 127.0.0.1:8000\r\n"
    )
    assert recv[2].startswith(b"GET / HTTP/1.1\r\nhost: example.com\r\n")


@pytest.mark.parametrize("status_code", [300, 304, 308, 401, 500])
async def test_proxy_tunnel_non_2xx_response(backend, status_code):
    raw_io = MockRawSocketBackend(
        data_to_send=(
            [
                b"HTTP/1.1 %d Not Good\r\n" % status_code,
                b"Date: Sun, 10 Oct 2010 23:26:07 GMT\r\n"
                b"Server: proxy-server\r\n"
                b"\r\n",
            ]
        ),
        backend=backend,
    )

    with pytest.raises(httpx.ProxyError) as e:
        async with httpx.HTTPProxy(
            proxy_url="http://127.0.0.1:8000",
            backend=raw_io,
            proxy_mode=httpx.HTTPProxyMode.TUNNEL_ONLY,
        ) as proxy:
            await proxy.request("GET", f"http://example.com")

    # ProxyError.request should be the CONNECT request not the original request
    assert e.value.request.method == "CONNECT"
    assert e.value.request.headers["Host"] == "127.0.0.1:8000"
    assert e.value.request.url.full_path == "example.com:80"

    # ProxyError.response should be the CONNECT response
    assert e.value.response.status_code == status_code
    assert e.value.response.headers["Server"] == "proxy-server"

    # Verify that the request wasn't sent after receiving an error from CONNECT
    recv = raw_io.received_data
    assert len(recv) == 2
    assert recv[0] == b"--- CONNECT(127.0.0.1, 8000) ---"
    assert recv[1].startswith(
        b"CONNECT example.com:80 HTTP/1.1\r\nhost: 127.0.0.1:8000\r\n"
    )


async def test_proxy_tunnel_start_tls(backend):
    raw_io = MockRawSocketBackend(
        data_to_send=(
            [
                b"HTTP/1.1 200 OK\r\n"
                b"Date: Sun, 10 Oct 2010 23:26:07 GMT\r\n"
                b"Server: proxy-server\r\n"
                b"\r\n",
                b"HTTP/1.1 404 Not Found\r\n"
                b"Date: Sun, 10 Oct 2010 23:26:07 GMT\r\n"
                b"Server: origin-server\r\n"
                b"\r\n",
            ]
        ),
        backend=backend,
    )
    async with httpx.HTTPProxy(
        proxy_url="http://127.0.0.1:8000",
        backend=raw_io,
        proxy_mode=httpx.HTTPProxyMode.TUNNEL_ONLY,
    ) as proxy:
        response = await proxy.request("GET", f"https://example.com")

        assert response.status_code == 404
        assert response.headers["Server"] == "origin-server"

        assert response.request.method == "GET"
        assert response.request.url == "https://example.com"
        assert response.request.headers["Host"] == "example.com"

    recv = raw_io.received_data
    assert len(recv) == 4
    assert recv[0] == b"--- CONNECT(127.0.0.1, 8000) ---"
    assert recv[1].startswith(
        b"CONNECT example.com:443 HTTP/1.1\r\nhost: 127.0.0.1:8000\r\n"
    )
    assert recv[2] == b"--- START_TLS(example.com) ---"
    assert recv[3].startswith(b"GET / HTTP/1.1\r\nhost: example.com\r\n")


@pytest.mark.parametrize(
    "proxy_mode", [httpx.HTTPProxyMode.FORWARD_ONLY, httpx.HTTPProxyMode.DEFAULT]
)
async def test_proxy_forwarding(backend, proxy_mode):
    raw_io = MockRawSocketBackend(
        data_to_send=(
            [
                b"HTTP/1.1 200 OK\r\n"
                b"Date: Sun, 10 Oct 2010 23:26:07 GMT\r\n"
                b"Server: origin-server\r\n"
                b"\r\n"
            ]
        ),
        backend=backend,
    )
    async with httpx.HTTPProxy(
        proxy_url="http://127.0.0.1:8000", backend=raw_io, proxy_mode=proxy_mode
    ) as proxy:
        response = await proxy.request("GET", f"http://example.com")

        assert response.status_code == 200
        assert response.headers["Server"] == "origin-server"

        assert response.request.method == "GET"
        assert response.request.url == "http://127.0.0.1:8000"
        assert response.request.url.full_path == "http://example.com"
        assert response.request.headers["Host"] == "example.com"

    recv = raw_io.received_data
    assert len(recv) == 2
    assert recv[0] == b"--- CONNECT(127.0.0.1, 8000) ---"
    assert recv[1].startswith(
        b"GET http://example.com HTTP/1.1\r\nhost: example.com\r\n"
    )


def test_proxy_url_with_username_and_password():
    proxy = httpx.HTTPProxy("http://user:password@example.com:1080")

    assert proxy.proxy_url == "http://example.com:1080"
    assert proxy.proxy_headers["Proxy-Authorization"] == "Basic dXNlcjpwYXNzd29yZA=="


def test_proxy_repr():
    proxy = httpx.HTTPProxy(
        "http://127.0.0.1:1080",
        proxy_headers={"Custom": "Header"},
        proxy_mode=httpx.HTTPProxyMode.DEFAULT,
    )

    assert repr(proxy) == (
        "HTTPProxy(proxy_url=URL('http://127.0.0.1:1080') "
        "proxy_headers=Headers({'custom': 'Header'}) "
        "proxy_mode=<HTTPProxyMode.DEFAULT: 'DEFAULT'>)"
    )
