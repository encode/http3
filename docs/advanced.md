# Advanced Usage

## Client Instances

Using a Client instance to make requests will give you HTTP connection pooling,
will provide cookie persistence, and allows you to apply configuration across
all outgoing requests.

!!! hint
    A Client instance is equivalent to a Session instance in `requests`.

### Usage

The recommended way to use a `Client` is as a context manager. This will ensure that connections are properly cleaned up when leaving the `with` block:

```python
>>> async with httpx.Client() as client:
...     r = await client.get('https://example.com')
...
>>> r
<Response [200 OK]>
```

Alternatively, you can explicitly close the connection pool without block-usage using `.close()`:

```python
>>> client = httpx.Client()
>>> try:
...     r = await client.get('https://example.com')
... finally:
...     await client.close()
...
>>> r
<Response [200 OK]>
```

Once you have a `Client`, you can use all the features documented in the [Quickstart](/quickstart) guide.

### Configuration

Clients allow you to apply configuration to all outgoing requests by passing parameters to the `Client` constructor.

For example, to apply a set of custom headers on every request:

```python
>>> url = 'http://httpbin.org/headers'
>>> headers = {'user-agent': 'my-app/0.0.1'}
>>> async with httpx.Client(headers=headers) as client:
...     r = await client.get(url)
...
>>> r.json()['headers']['User-Agent']
'my-app/0.0.1'
```

!!! note
    When you provide a parameter at both the client and request levels, one of two things can happen:

    - For headers, query parameters and cookies, the values are merged into one.
    - For all other parameters, the request-level value is used.

Additionally, `Client` constructor accepts some parameters that aren't available at the request level.

One particularly useful parameter is `base_url`, which allows you to define a base URL to prepend to all outgoing requests:

```python
>>> async with httpx.Client(base_url='http://httpbin.org') as client:
...     r = await client.get('/headers')
...
>>> r.request.url
URL('http://httpbin.org/headers')
```

For a list of all available client-level parameters, see the [`Client` API reference](/api/#client).

## Calling into Python Web Apps

You can configure an `httpx` client to call directly into a Python web
application using either the ASGI protocol.

This is particularly useful for two main use-cases:

* Using `httpx` as a client inside test cases.
* Mocking out external services during tests or in dev/staging environments.

Let's take this Starlette application as an example:

```python
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route


async def hello():
    return HTMLResponse("Hello World!")


app = Starlette(routes=[Route("/", hello)])
```

We can make requests directly against the application, like so:

```python
>>> import httpx
>>> async with httpx.Client(app=app) as client:
...     r = client.get('http://example/')
...     assert r.status_code == 200
...     assert r.text == "Hello World!"
```

For some more complex cases you might need to customize the WSGI or ASGI
dispatch. This allows you to:

* Inspect 500 error responses rather than raise exceptions by setting `raise_app_exceptions=False`.
* Mount the WSGI or ASGI application at a subpath by setting `root_path`.
* Use a given client address for requests by setting `client`.

For example:

```python
# Instantiate a client that makes WSGI requests with a client IP of "1.2.3.4".
dispatch = httpx.dispatch.ASGIDispatch(app=app, remote_addr="1.2.3.4")
async with httpx.Client(dispatch=dispatch) as client:
    ...
```

## Build Request

You can use `Client.build_request()` to build a request and
make modifications before sending the request.

```python
>>> async with httpx.Client() as client:
...     req = client.build_request("OPTIONS", "https://example.com")
...     req.url.full_path = "*"  # Build an 'OPTIONS *' request for CORS
...     r = await client.send(req)
...
>>> r
<Response [200 OK]>
```

## Specify the version of the HTTP protocol

One can set the version of the HTTP protocol for the client in case you want to make the requests using a specific version.

For example:

```python
async with httpx.Client(http_versions=["HTTP/1.1"]) as h11_client:
    h11_response = await h11_client.get("https://myserver.com")

async with httpx.Client(http_versions=["HTTP/2"]) as h2_client:
    h2_response = await h2_client.get("https://myserver.com")
```

## .netrc Support

HTTPX supports .netrc file. In `trust_env=True` cases, if auth parameter is
not defined, HTTPX tries to add auth into request's header from .netrc file.

!!! note
    The NETRC file is cached across requests made by a client.
    If you need to refresh the cache (e.g. because the NETRC file has changed),
    you should create a new client or restart the interpreter.

As default `trust_env` is true. To set false:
```python
>>> await httpx.get('https://example.org/', trust_env=False)
```

If `NETRC` environment is empty, HTTPX tries to use default files.
(`~/.netrc`, `~/_netrc`)

To change `NETRC` environment:
```python
>>> import os
>>> os.environ["NETRC"] = "my_default_folder/.my_netrc"
```

.netrc file content example:
```
machine netrcexample.org
login example-username
password example-password

...
```

## Unix Domain Sockets

You can configure an `httpx` client to connect through a unix domain socket via the `uds` parameter. This is useful when making requests to a server that is bound to a socket file rather than an IP address.

Here's an example requesting the Docker Engine API:

```python
import httpx


async with httpx.Client(uds="/var/run/docker.sock") as client:
    # This request will connect through the socket file.
    resp = await client.get("http://localhost/version")
```

## HTTP Proxying

HTTPX supports setting up proxies the same way that Requests does via the `proxies` parameter.
For example to forward all HTTP traffic to `http://127.0.0.1:3080` and all HTTPS traffic
to `http://127.0.0.1:3081` your `proxies` config would look like this:

```python
>>> proxies = {
...     "http": "http://127.0.0.1:3080",
...     "https": "http://127.0.0.1:3081"
... }
>>> async with httpx.Client(proxies=proxies) as client:
...     ...
```

Proxies can be configured for a specific scheme and host, all schemes of a host,
all hosts for a scheme, or for all requests. When determining which proxy configuration
to use for a given request this same order is used.

```python
>>> proxies = {
...     "http://example.com":  "...",  # Host+Scheme
...     "all://example.com":  "...",  # Host
...     "http": "...",  # Scheme
...     "all": "...",  # All
... }
>>> async with httpx.Client(proxies=proxies) as client:
...     ...
...
>>> proxy = "..."  # Shortcut for {'all': '...'}
>>> async with httpx.Client(proxies=proxy) as client:
...     ...
```

!!! warning
    To make sure that proxies cannot read your traffic,
    and even if the proxy_url uses HTTPS, it is recommended to
    use HTTPS and tunnel requests if possible.

By default `HTTPProxy` will operate as a forwarding proxy for `http://...` requests
and will establish a `CONNECT` TCP tunnel for `https://` requests. This doesn't change
regardless of the `proxy_url` being `http` or `https`.

Proxies can be configured to have different behavior such as forwarding or tunneling all requests:

```python
proxy = httpx.HTTPProxy(
    proxy_url="https://127.0.0.1",
    proxy_mode=httpx.HTTPProxyMode.TUNNEL_ONLY
)
async with httpx.Client(proxies=proxy) as client:
    # This request will be tunneled instead of forwarded.
    r = await client.get("http://example.com")
```

!!! note

    Per request proxy configuration, i.e. `client.get(url, proxies=...)`,
    has not been implemented yet. To use proxies you must pass the proxy
    information at `Client` initialization.

## Timeout fine-tuning

HTTPX offers various request timeout management options. Three types of timeouts
are available: **connect** timeouts, **write** timeouts and **read** timeouts.

* The **connect timeout** specifies the maximum amount of time to wait until
a connection to the requested host is established. If HTTPX is unable to connect
within this time frame, a `ConnectTimeout` exception is raised.
* The **write timeout** specifies the maximum duration to wait for a chunk of
data to be sent (for example, a chunk of the request body). If HTTPX is unable
to send data within this time frame, a `WriteTimeout` exception is raised.
* The **read timeout** specifies the maximum duration to wait for a chunk of
data to be received (for example, a chunk of the response body). If HTTPX is
unable to receive data within this time frame, a `ReadTimeout` exception is raised.

### Setting timeouts

You can set timeouts on two levels:

- For a given request:

```python
# Using top-level API
await httpx.get('http://example.com/api/v1/example', timeout=5)

# Or, with a client:
async with httpx.Client() as client:
    await client.get("http://example.com/api/v1/example", timeout=5)
```

- On a client instance, which results in the given `timeout` being used as a default for requests made with this client:

```python
async with httpx.Client(timeout=5) as client:
    await client.get('http://example.com/api/v1/example')
```

Besides, you can pass timeouts in two forms:

- A number, which sets the read, write and connect timeouts to the same value, as in the examples above.
- A `TimeoutConfig` instance, which allows to define the read, write and connect timeouts independently:

```python
timeout = httpx.TimeoutConfig(
    connect_timeout=5,
    read_timeout=10,
    write_timeout=15
)

resp = await httpx.get('http://example.com/api/v1/example', timeout=timeout)
```

### Default timeouts

By default all types of timeouts are set to 5 second.

### Disabling timeouts

To disable timeouts, you can pass `None` as a timeout parameter.
Note that currently this is not supported by the top-level API.

```python
url = "http://example.com/api/v1/delay/10"

await httpx.get(url, timeout=None)  # Times out after 5s


async with httpx.Client(timeout=None) as client:
    await client.get(url)  # Does not timeout, returns after 10s


timeout = httpx.TimeoutConfig(
    connect_timeout=5,
    read_timeout=None,
    write_timeout=5
)
await httpx.get(url, timeout=timeout) # Does not timeout, returns after 10s
```

## Multipart file encoding

As mentioned in the [quickstart](/quickstart#sending-multipart-file-uploads)
multipart file encoding is available by passing a dictionary with the
name of the payloads as keys and a tuple of elements as values.

```python
>>> files = {'upload-file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel')}
>>> r = await httpx.post("https://httpbin.org/post", files=files)
>>> print(r.text)
{
  ...
  "files": {
    "upload-file": "<... binary content ...>"
  },
  ...
}
```

More specifically, this tuple must have at least two elements and maximum of three:
- The first one is an optional file name which can be set to `None`.
- The second may be a file-like object or a string which will be automatically
encoded in UTF-8.
- An optional third element can be included with the
[MIME type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_Types)
of the file being uploaded. If not specified HTTPX will attempt to guess the MIME type
based on the file name specified as the first element or the tuple, if that
is set to `None` or it cannot be inferred from it, HTTPX will default to
`applicaction/octet-stream`.

```python
>>> files = {'upload-file': (None, 'text content', 'text/plain')}
>>> r = await httpx.post("https://httpbin.org/post", files=files)
>>> print(r.text)
{
  ...
  "files": {},
  "form": {
    "upload-file": "text-content"
  },
  ...
}
```

## SSL certificates

When making a request over HTTPS, HTTPX needs to verify the identity of the requested host. To do this, it uses a bundle of SSL certificates (a.k.a. CA bundle) delivered by a trusted certificate authority (CA).

### Default CA bundle

By default, HTTPX uses the CA bundle provided by [Certifi](https://pypi.org/project/certifi/). This is what you want in most cases, even though some advanced situations may require you to use a different set of certificates.

### Using a custom CA bundle

If you'd like to use a custom CA bundle, you can use the `verify` parameter that is available on the high-level API as well as clients. For example:

```python
import httpx

r = await httpx.get("https://example.org", verify="path/to/client.pem")
```

### Making HTTPS requests to a local server

When making requests to local servers, such as a development server running on `localhost`, you will typically be using unencrypted HTTP connections.

If you do need to make HTTPS connections to a local server, for example to test an HTTPS-only service, you will need to create and use your own certificates. Here's one way to do it:

1. Use [trustme-cli](https://github.com/sethmlarson/trustme-cli/) to generate a pair of server key/cert files, and a client cert file.
1. Pass the server key/cert files when starting your local server. (This depends on the particular web server you're using. For example, [Uvicorn](https://www.uvicorn.org) provides the `--ssl-keyfile` and `--ssl-certfile` options.)
1. Tell HTTPX to use the certificates stored in `client.pem`:

```python
>>> import httpx
>>> r = await httpx.get("https://localhost:8000", verify="/tmp/client.pem")
>>> r
Response <200 OK>
```

## Support async environments

### [asyncio](https://docs.python.org/3/library/asyncio.html) (Default)

By default, `AsyncClient` uses `asyncio` to perform asynchronous operations and I/O calls.

### [trio](https://github.com/python-trio/trio)

To make asynchronous requests in `trio` programs, pass a `TrioBackend` to the `AsyncClient`:

```python
import trio
import httpx
from httpx.concurrency.trio import TrioBackend

async def main():
    async with httpx.AsyncClient(backend=TrioBackend()) as client:
        ...

trio.run(main)
```

!!! important
    `trio` must be installed to import and use the `TrioBackend`.
