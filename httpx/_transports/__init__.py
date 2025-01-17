import sys

from .asgi import *
from .base import *
from .mock import *
from .wsgi import *

if sys.platform == "emscripten":  # pragma: nocover
    # in emscripten we use javascript fetch
    from .jsfetch import *

    # override default transport names
    HTTPTransport = JavascriptFetchTransport
    AsyncHTTPTransport = AsyncJavascriptFetchTransport
else:
    # everywhere else we use httpcore
    from .httpcore import *

    HTTPTransport = HTTPCoreTransport
    AsyncHTTPTransport = AsyncHTTPCoreTransport

__all__ = [
    "ASGITransport",
    "AsyncBaseTransport",
    "BaseTransport",
    "AsyncHTTPTransport",
    "HTTPTransport",
    "MockTransport",
    "WSGITransport",
]
