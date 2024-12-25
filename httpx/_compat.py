import sys

if sys.version_info >= (3, 10):
    from contextlib import aclosing
else:
    from contextlib import asynccontextmanager
    from typing import Any, AsyncIterator, Awaitable, Protocol, TypeVar

    class _SupportsAclose(Protocol):
        def aclose(self) -> Awaitable[object]: ...

    _SupportsAcloseT = TypeVar("_SupportsAcloseT", bound=_SupportsAclose)

    @asynccontextmanager
    async def aclosing(thing: _SupportsAcloseT) -> AsyncIterator[Any]:
        try:
            yield thing
        finally:
            await thing.aclose()


__all__ = ["aclosing"]
