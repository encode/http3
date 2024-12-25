import typing

import pytest

import httpx


def redirects(request: httpx.Request) -> httpx.Response:
    if request.url.scheme not in ("http", "https"):
        raise httpx.UnsupportedProtocol(f"Scheme {request.url.scheme!r} not supported.")

    if request.url.path == "/redirect_301":
        status_code = httpx.codes.MOVED_PERMANENTLY
        content = b"<a href='https://example.org/'>here</a>"
        headers = {"location": "https://example.org/"}
        return httpx.Response(status_code, headers=headers, content=content)

    elif request.url.path == "/redirect_302":
        status_code = httpx.codes.FOUND
        headers = {"location": "https://example.org/"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/redirect_303":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "https://example.org/"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/relative_redirect":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "/"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/malformed_redirect":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "https://:443/"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/invalid_redirect":
        status_code = httpx.codes.SEE_OTHER
        raw_headers = [(b"location", "https://😇/".encode("utf-8"))]
        return httpx.Response(status_code, headers=raw_headers)

    elif request.url.path == "/no_scheme_redirect":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "//example.org/"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/multiple_redirects":
        params = httpx.QueryParams(request.url.query)
        count = int(params.get("count", "0"))
        redirect_count = count - 1
        status_code = httpx.codes.SEE_OTHER if count else httpx.codes.OK
        if count:
            location = "/multiple_redirects"
            if redirect_count:
                location += f"?count={redirect_count}"
            headers = {"location": location}
        else:
            headers = {}
        return httpx.Response(status_code, headers=headers)

    if request.url.path == "/redirect_loop":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "/redirect_loop"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/cross_domain":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "https://example.org/cross_domain_target"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/cross_domain_target":
        status_code = httpx.codes.OK
        data = {
            "body": request.content.decode("ascii"),
            "headers": dict(request.headers),
        }
        return httpx.Response(status_code, json=data)

    elif request.url.path == "/redirect_body":
        status_code = httpx.codes.PERMANENT_REDIRECT
        headers = {"location": "/redirect_body_target"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/redirect_no_body":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "/redirect_body_target"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/redirect_body_target":
        data = {
            "body": request.content.decode("ascii"),
            "headers": dict(request.headers),
        }
        return httpx.Response(200, json=data)

    elif request.url.path == "/cross_subdomain":
        if request.headers["Host"] != "www.example.org":
            status_code = httpx.codes.PERMANENT_REDIRECT
            headers = {"location": "https://www.example.org/cross_subdomain"}
            return httpx.Response(status_code, headers=headers)
        else:
            return httpx.Response(200, text="Hello, world!")

    elif request.url.path == "/redirect_custom_scheme":
        status_code = httpx.codes.MOVED_PERMANENTLY
        headers = {"location": "market://details?id=42"}
        return httpx.Response(status_code, headers=headers)

    elif request.url.path == "/redirect_303_with_history":
        status_code = httpx.codes.SEE_OTHER
        headers = {"location": "https://example.org/"}
        history = [httpx.Response(status_code, headers=headers)]
        return httpx.Response(status_code, headers=headers, history=history)

    if request.method == "HEAD":
        return httpx.Response(200)

    return httpx.Response(200, html="<html><body>Hello, world!</body></html>")


def test_redirect_301():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.post("https://example.org/redirect_301", follow_redirects=True)
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_redirect_302():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.post("https://example.org/redirect_302", follow_redirects=True)
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_redirect_303():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get("https://example.org/redirect_303", follow_redirects=True)
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_next_request():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    request = client.build_request("POST", "https://example.org/redirect_303")
    response = client.send(request, follow_redirects=False)
    assert response.status_code == httpx.codes.SEE_OTHER
    assert response.url == "https://example.org/redirect_303"
    assert response.next_request is not None

    response = client.send(response.next_request, follow_redirects=False)
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert response.next_request is None


@pytest.mark.anyio
async def test_async_next_request():
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirects)) as client:
        request = client.build_request("POST", "https://example.org/redirect_303")
        response = await client.send(request, follow_redirects=False)
        assert response.status_code == httpx.codes.SEE_OTHER
        assert response.url == "https://example.org/redirect_303"
        assert response.next_request is not None

        response = await client.send(response.next_request, follow_redirects=False)
        assert response.status_code == httpx.codes.OK
        assert response.url == "https://example.org/"
        assert response.next_request is None


def test_head_redirect():
    """
    Contrary to Requests, redirects remain enabled by default for HEAD requests.
    """
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.head("https://example.org/redirect_302", follow_redirects=True)
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert response.request.method == "HEAD"
    assert len(response.history) == 1
    assert response.text == ""


def test_relative_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get(
        "https://example.org/relative_redirect", follow_redirects=True
    )
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_malformed_redirect():
    # https://github.com/encode/httpx/issues/771
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get(
        "http://example.org/malformed_redirect", follow_redirects=True
    )
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org:443/"
    assert len(response.history) == 1


def test_invalid_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    with pytest.raises(httpx.RemoteProtocolError):
        client.get("http://example.org/invalid_redirect", follow_redirects=True)


def test_no_scheme_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get(
        "https://example.org/no_scheme_redirect", follow_redirects=True
    )
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 1


def test_fragment_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get(
        "https://example.org/relative_redirect#fragment", follow_redirects=True
    )
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/#fragment"
    assert len(response.history) == 1


def test_multiple_redirects():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get(
        "https://example.org/multiple_redirects?count=20", follow_redirects=True
    )
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/multiple_redirects"
    assert len(response.history) == 20
    assert response.history[0].url == "https://example.org/multiple_redirects?count=20"
    assert response.history[1].url == "https://example.org/multiple_redirects?count=19"
    assert len(response.history[0].history) == 0
    assert len(response.history[1].history) == 1


@pytest.mark.anyio
async def test_async_too_many_redirects():
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirects)) as client:
        with pytest.raises(httpx.TooManyRedirects):
            await client.get(
                "https://example.org/multiple_redirects?count=21", follow_redirects=True
            )


def test_sync_too_many_redirects():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    with pytest.raises(httpx.TooManyRedirects):
        client.get(
            "https://example.org/multiple_redirects?count=21", follow_redirects=True
        )


def test_redirect_loop():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    with pytest.raises(httpx.TooManyRedirects):
        client.get("https://example.org/redirect_loop", follow_redirects=True)


def test_cross_domain_redirect_with_auth_header():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.com/cross_domain"
    headers = {"Authorization": "abc"}
    response = client.get(url, headers=headers, follow_redirects=True)
    assert response.url == "https://example.org/cross_domain_target"
    assert "authorization" not in response.json()["headers"]


def test_cross_domain_https_redirect_with_auth_header():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "http://example.com/cross_domain"
    headers = {"Authorization": "abc"}
    response = client.get(url, headers=headers, follow_redirects=True)
    assert response.url == "https://example.org/cross_domain_target"
    assert "authorization" not in response.json()["headers"]


def test_cross_domain_redirect_with_auth():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.com/cross_domain"
    response = client.get(url, auth=("user", "pass"), follow_redirects=True)
    assert response.url == "https://example.org/cross_domain_target"
    assert "authorization" not in response.json()["headers"]


def test_same_domain_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.org/cross_domain"
    headers = {"Authorization": "abc"}
    response = client.get(url, headers=headers, follow_redirects=True)
    assert response.url == "https://example.org/cross_domain_target"
    assert response.json()["headers"]["authorization"] == "abc"


def test_same_domain_https_redirect_with_auth_header():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "http://example.org/cross_domain"
    headers = {"Authorization": "abc"}
    response = client.get(url, headers=headers, follow_redirects=True)
    assert response.url == "https://example.org/cross_domain_target"
    assert response.json()["headers"]["authorization"] == "abc"


def test_body_redirect():
    """
    A 308 redirect should preserve the request body.
    """
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.org/redirect_body"
    content = b"Example request body"
    response = client.post(url, content=content, follow_redirects=True)
    assert response.url == "https://example.org/redirect_body_target"
    assert response.json()["body"] == "Example request body"
    assert "content-length" in response.json()["headers"]


def test_no_body_redirect():
    """
    A 303 redirect should remove the request body.
    """
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.org/redirect_no_body"
    content = b"Example request body"
    response = client.post(url, content=content, follow_redirects=True)
    assert response.url == "https://example.org/redirect_body_target"
    assert response.json()["body"] == ""
    assert "content-length" not in response.json()["headers"]


def test_can_stream_if_no_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.org/redirect_301"
    with client.stream("GET", url, follow_redirects=False) as response:
        pass
    assert response.status_code == httpx.codes.MOVED_PERMANENTLY
    assert response.headers["location"] == "https://example.org/"


class ConsumeBodyTransport(httpx.MockTransport):
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        assert isinstance(request.stream, httpx.SyncByteStream)
        list(request.stream)
        return self.handler(request)  # type: ignore[return-value]


def test_cannot_redirect_streaming_body():
    client = httpx.Client(transport=ConsumeBodyTransport(redirects))
    url = "https://example.org/redirect_body"

    def streaming_body() -> typing.Iterator[bytes]:
        yield b"Example request body"  # pragma: no cover

    with pytest.raises(httpx.StreamConsumed):
        client.post(url, content=streaming_body(), follow_redirects=True)


def test_cross_subdomain_redirect():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    url = "https://example.com/cross_subdomain"
    response = client.get(url, follow_redirects=True)
    assert response.url == "https://www.example.org/cross_subdomain"


def cookie_sessions(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/":
        cookie = request.headers.get("Cookie")
        if cookie is not None:
            content = b"Logged in"
        else:
            content = b"Not logged in"
        return httpx.Response(200, content=content)

    elif request.url.path == "/login":
        status_code = httpx.codes.SEE_OTHER
        headers = {
            "location": "/",
            "set-cookie": (
                "session=eyJ1c2VybmFtZSI6ICJ0b21; path=/; Max-Age=1209600; "
                "httponly; samesite=lax"
            ),
        }
        return httpx.Response(status_code, headers=headers)

    else:
        assert request.url.path == "/logout"
        status_code = httpx.codes.SEE_OTHER
        headers = {
            "location": "/",
            "set-cookie": (
                "session=null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; "
                "httponly; samesite=lax"
            ),
        }
        return httpx.Response(status_code, headers=headers)


def test_redirect_cookie_behavior():
    client = httpx.Client(
        transport=httpx.MockTransport(cookie_sessions), follow_redirects=True
    )

    # The client is not logged in.
    response = client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"

    # Login redirects to the homepage, setting a session cookie.
    response = client.post("https://example.com/login")
    assert response.url == "https://example.com/"
    assert response.text == "Logged in"

    # The client is logged in.
    response = client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Logged in"

    # Logout redirects to the homepage, expiring the session cookie.
    response = client.post("https://example.com/logout")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"

    # The client is not logged in.
    response = client.get("https://example.com/")
    assert response.url == "https://example.com/"
    assert response.text == "Not logged in"


def test_redirect_custom_scheme():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    with pytest.raises(httpx.UnsupportedProtocol) as e:
        client.post("https://example.org/redirect_custom_scheme", follow_redirects=True)
    assert str(e.value) == "Scheme 'market' not supported."


@pytest.mark.anyio
async def test_async_invalid_redirect():
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirects)) as client:
        with pytest.raises(httpx.RemoteProtocolError):
            await client.get(
                "http://example.org/invalid_redirect", follow_redirects=True
            )


def test_redirect_303_history():
    client = httpx.Client(transport=httpx.MockTransport(redirects))
    response = client.get(
        "https://example.org/redirect_303_with_history", follow_redirects=True
    )
    assert response.status_code == httpx.codes.OK
    assert response.url == "https://example.org/"
    assert len(response.history) == 2


@pytest.mark.anyio
async def test_async_redirect_history():
    async with httpx.AsyncClient(transport=httpx.MockTransport(redirects)) as client:
        request = client.build_request(
            "POST", "https://example.org/redirect_303_with_history"
        )
        response = await client.send(request, follow_redirects=True)
        assert response.status_code == httpx.codes.OK
        assert response.url == "https://example.org/"
        assert len(response.history) == 2
