# HTTP/2

HTTP/2 is a major new iteration of the HTTP protocol, that provides a far more
efficient transport, with potential performance benefits. HTTP/2 does not change
the core semantics of the request or response, but alters the way that data is
sent to and from the server.

Rather than the text format that HTTP/1.1 uses, HTTP/2 is a binary format.
The binary format provides full request and response multiplexing, and efficient
compression of HTTP headers. The stream multiplexing means that where HTTP/1.1
requires one TCP stream for each concurrent request, HTTP/2 allows a single TCP
stream to handle multiple concurrent requests.

HTTP/2 also provides support for functionality such as response prioritization,
and server push.

For a comprehensive guide to HTTP/2 you may want to check out "[http2 explained](https://http2-explained.haxx.se/)".

## Enabling HTTP/2

When using the `httpx` client, HTTP/2 support is not enabled by default, because
HTTP/1.1 is a mature, battle-hardened transport layer, and our HTTP/1.1
implementation may be considered the more robust option at this point in time.
It is possible that a future version of `httpx` may enable HTTP/2 support by default.

If you're issuing highly concurrent requests you might want to consider
trying out our HTTP/2 support. You can do so by first making sure to install
the optional HTTP/2 dependencies...

```shell
$ pip install httpx[http2]
```

And then instantiating a client with HTTP/2 support enabled:

```python
client = httpx.AsyncClient(http2=True)
...
```

You can also instantiate a client as a context manager, to ensure that all
HTTP connections are nicely scoped, and will be closed once the context block
is exited.

```python
async with httpx.AsyncClient(http2=True) as client:
    ...
```

HTTP/2 support is available on both `Client` and `AsyncClient`, although it's
typically more useful in async contexts if you're issuing lots of concurrent
requests.

## Inspecting the HTTP version

Enabling HTTP/2 support on the client does not *necessarily* mean that your
requests and responses will be transported over HTTP/2, since both the client
*and* the server need to support HTTP/2. If you connect to a server that only
supports HTTP/1.1 the client will use a standard HTTP/1.1 connection instead.

To force HTTP/2 to be enabled, disable HTTP/1.1. Otherwise, the client will try to use HTTP/1.1
```python
client = httpx.AsyncClient(http1=False, http2=True)
# or
async with httpx.AsyncClient(http1=False, http2=True) as client:
```

You can determine which version of the HTTP protocol was used by examining
the `.http_version` property on the response.

```python
client = httpx.AsyncClient(http2=True)
response = await client.get(...)
print(response.http_version)  # "HTTP/1.0", "HTTP/1.1", or "HTTP/2".
```
