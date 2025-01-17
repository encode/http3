import asyncio
import json
import os
import threading
import time
import typing
from pathlib import Path

import pytest
import trustme
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    load_pem_private_key,
)
from uvicorn.config import Config
from uvicorn.server import Server

import httpx
from tests.concurrency import sleep

ENVIRONMENT_VARIABLES = {
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "SSLKEYLOGFILE",
}


@pytest.fixture(scope="function", autouse=True)
def clean_environ():
    """Keeps os.environ clean for every test without having to mock os.environ"""
    original_environ = os.environ.copy()
    os.environ.clear()
    os.environ.update(
        {
            k: v
            for k, v in original_environ.items()
            if k not in ENVIRONMENT_VARIABLES and k.lower() not in ENVIRONMENT_VARIABLES
        }
    )
    yield
    os.environ.clear()
    os.environ.update(original_environ)


Message = typing.Dict[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[
    [typing.Dict[str, typing.Any]], typing.Coroutine[None, None, None]
]
Scope = typing.Dict[str, typing.Any]


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    assert scope["type"] == "http"
    if scope["path"].startswith("/slow_response"):
        await slow_response(scope, receive, send)
    elif scope["path"].startswith("/status"):
        await status_code(scope, receive, send)
    elif scope["path"].startswith("/echo_body"):
        await echo_body(scope, receive, send)
    elif scope["path"].startswith("/echo_binary"):
        await echo_binary(scope, receive, send)
    elif scope["path"].startswith("/echo_headers"):
        await echo_headers(scope, receive, send)
    elif scope["path"].startswith("/redirect_301"):
        await redirect_301(scope, receive, send)
    elif scope["path"].startswith("/json"):
        await hello_world_json(scope, receive, send)
    elif scope["path"].startswith("/wheel_download"):  # pragma: nocover for emscripten
        await wheel_download(scope, receive, send)
    elif scope["path"].startswith("/emscripten"):  # pragma: nocover for emscripten
        await hello_world_emscripten(scope, receive, send)
    else:
        await hello_world(scope, receive, send)


async def hello_world(scope: Scope, receive: Receive, send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


# For testing on emscripten, we require cross origin isolation headers
# to be set or else browsers won't be able to read from us from javascript
async def hello_world_emscripten(
    scope: Scope, receive: Receive, send: Send
) -> None:  # pragma: nocover for emscripten
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/plain"],
                [b"access-control-allow-origin", "*"],
                [
                    b"access-control-allow-methods",
                    b"PUT, GET, HEAD, POST, DELETE, OPTIONS",
                ],
                [b"Access-Control-Allow-Headers", b"*"],
            ],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


# For testing on emscripten, it is useful to be able to
# get the wheel package so that we can install it e.g.
# on web-workers
async def wheel_download(
    scope: Scope, receive: Receive, send: Send
) -> None:  # pragma: nocover for emscripten
    wheel_file = list(Path("dist").glob("*.whl"))[0]
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"application/x-wheel"],
                [b"access-control-allow-origin", "*"],
                [
                    b"access-control-allow-methods",
                    b"PUT, GET, HEAD, POST, DELETE, OPTIONS",
                ],
                [b"Access-Control-Allow-Headers", b"*"],
            ],
        }
    )
    wheel_bytes = wheel_file.read_bytes()
    await send({"type": "http.response.body", "body": wheel_bytes})


async def hello_world_json(scope: Scope, receive: Receive, send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": b'{"Hello": "world!"}'})


async def slow_response(scope: Scope, receive: Receive, send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/plain"],
                [b"access-control-allow-origin", "*"],
                [
                    b"access-control-allow-methods",
                    b"PUT, GET, HEAD, POST, DELETE, OPTIONS",
                ],
                [b"Access-Control-Allow-Headers", b"*"],
                [b"Cache-control", "no-store,private,no-cache,must-revalidate"],
            ],
        }
    )
    await sleep(1.0)  # Allow triggering a read timeout.
    await send({"type": "http.response.body", "body": b"Hello, world!"})


async def status_code(scope: Scope, receive: Receive, send: Send) -> None:
    status_code = int(scope["path"].replace("/status/", ""))
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": b"Hello, world!"})


async def echo_body(scope: Scope, receive: Receive, send: Send) -> None:
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/plain"]],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def echo_binary(scope: Scope, receive: Receive, send: Send) -> None:
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/octet-stream"]],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def echo_headers(scope: Scope, receive: Receive, send: Send) -> None:
    body = {
        name.capitalize().decode(): value.decode()
        for name, value in scope.get("headers", [])
    }
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": json.dumps(body).encode()})


async def redirect_301(scope: Scope, receive: Receive, send: Send) -> None:
    await send(
        {"type": "http.response.start", "status": 301, "headers": [[b"location", b"/"]]}
    )
    await send({"type": "http.response.body"})


@pytest.fixture(scope="session")
def cert_authority():
    return trustme.CA()


@pytest.fixture(scope="session")
def localhost_cert(cert_authority):
    return cert_authority.issue_cert("localhost")


@pytest.fixture(scope="session")
def cert_pem_file(localhost_cert):
    with localhost_cert.cert_chain_pems[0].tempfile() as tmp:
        yield tmp


@pytest.fixture(scope="session")
def cert_private_key_file(localhost_cert):
    with localhost_cert.private_key_pem.tempfile() as tmp:
        yield tmp


@pytest.fixture(scope="session")
def cert_encrypted_private_key_file(localhost_cert):
    # Deserialize the private key and then reserialize with a password
    private_key = load_pem_private_key(
        localhost_cert.private_key_pem.bytes(), password=None, backend=default_backend()
    )
    encrypted_private_key_pem = trustme.Blob(
        private_key.private_bytes(
            Encoding.PEM,
            PrivateFormat.TraditionalOpenSSL,
            BestAvailableEncryption(password=b"password"),
        )
    )
    with encrypted_private_key_pem.tempfile() as tmp:
        yield tmp


class TestServer(Server):
    @property
    def url(self) -> httpx.URL:
        protocol = "https" if self.config.is_ssl else "http"
        return httpx.URL(f"{protocol}://{self.config.host}:{self.config.port}/")

    def install_signal_handlers(self) -> None:
        # Disable the default installation of handlers for signals such as SIGTERM,
        # because it can only be done in the main thread.
        pass  # pragma: nocover

    async def serve(self, sockets=None):
        self.restart_requested = asyncio.Event()

        loop = asyncio.get_event_loop()
        tasks = {
            loop.create_task(super().serve(sockets=sockets)),
            loop.create_task(self.watch_restarts()),
        }
        await asyncio.wait(tasks)

    async def restart(self) -> None:  # pragma: no cover
        # This coroutine may be called from a different thread than the one the
        # server is running on, and from an async environment that's not asyncio.
        # For this reason, we use an event to coordinate with the server
        # instead of calling shutdown()/startup() directly, and should not make
        # any asyncio-specific operations.
        self.started = False
        self.restart_requested.set()
        while not self.started:
            await sleep(0.2)

    async def watch_restarts(self) -> None:  # pragma: no cover
        while True:
            if self.should_exit:
                return

            try:
                await asyncio.wait_for(self.restart_requested.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            self.restart_requested.clear()
            await self.shutdown()
            await self.startup()


def serve_in_thread(server: TestServer) -> typing.Iterator[TestServer]:
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        while not server.started:
            time.sleep(1e-3)
        yield server
    finally:
        server.should_exit = True
        thread.join()


@pytest.fixture(scope="session")
def server() -> typing.Iterator[TestServer]:
    config = Config(app=app, lifespan="off", loop="asyncio")
    server = TestServer(config=config)
    yield from serve_in_thread(server)


# a local https server is need for emscripten tests
# to work
@pytest.fixture(scope="session")
def https_server(
    cert_pem_file, cert_private_key_file
):  # pragma: nocover (only used by emscripten)
    config = Config(
        app=app,
        lifespan="off",
        ssl_certfile=cert_pem_file,
        ssl_keyfile=cert_private_key_file,
        port=8001,
        loop="asyncio",
    )
    server = TestServer(config=config)
    yield from serve_in_thread(server)
