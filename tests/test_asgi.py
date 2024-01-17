import json

import anyio
import pytest

import httpx


async def hello_world(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_path(scope, receive, send):
    status = 200
    output = json.dumps({"path": scope["path"]}).encode("utf-8")
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_raw_path(scope, receive, send):
    status = 200
    output = json.dumps({"raw_path": scope["raw_path"].decode("ascii")}).encode("utf-8")
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def echo_body(scope, receive, send):
    status = 200
    headers = [(b"content-type", "text/plain")]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    more_body = True
    while more_body:
        message = await receive()
        body = message.get("body", b"")
        more_body = message.get("more_body", False)
        await send({"type": "http.response.body", "body": body, "more_body": more_body})


async def echo_headers(scope, receive, send):
    status = 200
    output = json.dumps(
        {"headers": [[k.decode(), v.decode()] for k, v in scope["headers"]]}
    ).encode("utf-8")
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})


async def raise_exc(scope, receive, send):
    raise RuntimeError()


async def raise_exc_after_response_start(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await anyio.sleep(0)
    raise RuntimeError()


async def raise_exc_after_response(scope, receive, send):
    status = 200
    output = b"Hello, World!"
    headers = [(b"content-type", "text/plain"), (b"content-length", str(len(output)))]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": output})
    await anyio.sleep(0)
    raise RuntimeError()


@pytest.mark.anyio
async def test_asgi_transport():
    async with httpx.ASGITransport(app=hello_world) as transport:
        request = httpx.Request("GET", "http://www.example.com/")
        response = await transport.handle_async_request(request)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b"Hello, World!"


@pytest.mark.anyio
async def test_asgi_transport_no_body():
    async with httpx.ASGITransport(app=echo_body) as transport:
        request = httpx.Request("GET", "http://www.example.com/")
        response = await transport.handle_async_request(request)
        await response.aread()
        assert response.status_code == 200
        assert response.content == b""


@pytest.mark.anyio
async def test_asgi():
    async with httpx.AsyncClient(app=hello_world) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.text == "Hello, World!"


@pytest.mark.anyio
async def test_asgi_urlencoded_path():
    async with httpx.AsyncClient(app=echo_path) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"path": "/user@example.org"}


@pytest.mark.anyio
async def test_asgi_raw_path():
    async with httpx.AsyncClient(app=echo_raw_path) as client:
        url = httpx.URL("http://www.example.org/").copy_with(path="/user@example.org")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"raw_path": "/user@example.org"}


@pytest.mark.anyio
async def test_asgi_raw_path_should_not_include_querystring_portion():
    """
    See https://github.com/encode/httpx/issues/2810
    """
    async with httpx.AsyncClient(app=echo_raw_path) as client:
        url = httpx.URL("http://www.example.org/path?query")
        response = await client.get(url)

    assert response.status_code == 200
    assert response.json() == {"raw_path": "/path"}


@pytest.mark.anyio
async def test_asgi_upload():
    async with httpx.AsyncClient(app=echo_body) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert response.text == "example"


@pytest.mark.anyio
async def test_asgi_headers():
    async with httpx.AsyncClient(app=echo_headers) as client:
        response = await client.get("http://www.example.org/")

    assert response.status_code == 200
    assert response.json() == {
        "headers": [
            ["host", "www.example.org"],
            ["accept", "*/*"],
            ["accept-encoding", "gzip, deflate, br"],
            ["connection", "keep-alive"],
            ["user-agent", f"python-httpx/{httpx.__version__}"],
        ]
    }


@pytest.mark.anyio
async def test_asgi_exc():
    async with httpx.AsyncClient(app=raise_exc) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_exc_after_response_start():
    transport = httpx.ASGITransport(app=raise_exc_after_response_start)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_exc_after_response():
    async with httpx.AsyncClient(app=raise_exc_after_response) as client:
        with pytest.raises(RuntimeError):
            await client.get("http://www.example.org/")


@pytest.mark.anyio
async def test_asgi_disconnect_after_response_complete():
    disconnect = False

    async def read_body(scope, receive, send):
        nonlocal disconnect

        status = 200
        headers = [(b"content-type", "text/plain")]

        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        more_body = True
        while more_body:
            message = await receive()
            more_body = message.get("more_body", False)

        await send({"type": "http.response.body", "body": b"", "more_body": False})

        # The ASGI spec says of the Disconnect message:
        # "Sent to the application when a HTTP connection is closed or if receive is
        # called after a response has been sent."
        # So if receive() is called again, the disconnect message should be received
        message = await receive()
        disconnect = message.get("type") == "http.disconnect"

    async with httpx.AsyncClient(app=read_body) as client:
        response = await client.post("http://www.example.org/", content=b"example")

    assert response.status_code == 200
    assert disconnect


@pytest.mark.anyio
async def test_asgi_exc_no_raise():
    transport = httpx.ASGITransport(app=raise_exc, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 500


@pytest.mark.anyio
async def test_asgi_exc_no_raise_after_response_start():
    transport = httpx.ASGITransport(
        app=raise_exc_after_response_start, raise_app_exceptions=False
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 200


@pytest.mark.anyio
async def test_asgi_exc_no_raise_after_response():
    transport = httpx.ASGITransport(
        app=raise_exc_after_response, raise_app_exceptions=False
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("http://www.example.org/")

        assert response.status_code == 200


@pytest.mark.anyio
async def test_asgi_stream_returns_before_waiting_for_body():
    start_response_body = anyio.Event()

    async def send_response_body_after_event(scope, receive, send):
        status = 200
        headers = [(b"content-type", b"text/plain")]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await start_response_body.wait()
        await send({"type": "http.response.body", "body": b"body", "more_body": False})

    transport = httpx.ASGITransport(app=send_response_body_after_event)
    async with httpx.AsyncClient(transport=transport) as client:
        async with client.stream("GET", "http://www.example.org/") as response:
            assert response.status_code == 200
            start_response_body.set()
            await response.aread()
            assert response.text == "body"


@pytest.mark.anyio
async def test_asgi_stream_allows_iterative_streaming():
    stream_events = [anyio.Event() for i in range(4)]

    async def send_response_body_after_event(scope, receive, send):
        status = 200
        headers = [(b"content-type", b"text/plain")]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        for e in stream_events:
            await e.wait()
            await send(
                {
                    "type": "http.response.body",
                    "body": b"chunk",
                    "more_body": e is not stream_events[-1],
                }
            )

    transport = httpx.ASGITransport(app=send_response_body_after_event)
    async with httpx.AsyncClient(transport=transport) as client:
        async with client.stream("GET", "http://www.example.org/") as response:
            assert response.status_code == 200
            iterator = response.aiter_raw()
            for e in stream_events:
                e.set()
                assert await iterator.__anext__() == b"chunk"
            with pytest.raises(StopAsyncIteration):
                await iterator.__anext__()


@pytest.mark.anyio
async def test_asgi_can_be_canceled():
    # This test exists to cover transmission of the cancellation exception through
    # _AwaitableRunner
    app_started = anyio.Event()

    async def never_return(scope, receive, send):
        app_started.set()
        await anyio.sleep_forever()

    transport = httpx.ASGITransport(app=never_return)
    async with httpx.AsyncClient(transport=transport) as client:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(client.get, "http://www.example.org/")
            await app_started.wait()
            task_group.cancel_scope.cancel()
