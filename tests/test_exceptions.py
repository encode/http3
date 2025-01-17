from __future__ import annotations

import pickle
import typing

import httpcore
import pytest

import httpx

if typing.TYPE_CHECKING:  # pragma: no cover
    from conftest import TestServer


def test_httpcore_all_exceptions_mapped() -> None:
    """
    All exception classes exposed by HTTPCore are properly mapped to an HTTPX-specific
    exception class.
    """
    expected_mapped_httpcore_exceptions = {
        value.__name__
        for _, value in vars(httpcore).items()
        if isinstance(value, type)
        and issubclass(value, Exception)
        and value is not httpcore.ConnectionNotAvailable
    }

    httpx_exceptions = {
        value.__name__
        for _, value in vars(httpx).items()
        if isinstance(value, type) and issubclass(value, Exception)
    }

    unmapped_exceptions = expected_mapped_httpcore_exceptions - httpx_exceptions

    if unmapped_exceptions:  # pragma: no cover
        pytest.fail(f"Unmapped httpcore exceptions: {unmapped_exceptions}")


def test_httpcore_exception_mapping(server: TestServer) -> None:
    """
    HTTPCore exception mapping works as expected.
    """
    impossible_port = 123456
    with pytest.raises(httpx.ConnectError):
        httpx.get(server.url.copy_with(port=impossible_port))

    with pytest.raises(httpx.ReadTimeout):
        httpx.get(
            server.url.copy_with(path="/slow_response"),
            timeout=httpx.Timeout(5, read=0.01),
        )


def test_request_attribute() -> None:
    # Exception without request attribute
    exc = httpx.ReadTimeout("Read operation timed out")
    with pytest.raises(RuntimeError):
        exc.request  # noqa: B018

    # Exception with request attribute
    request = httpx.Request("GET", "https://www.example.com")
    exc = httpx.ReadTimeout("Read operation timed out", request=request)
    assert exc.request == request


def test_pickle_error(server):
    with httpx.Client() as client:
        response = client.request("GET", server.url.copy_with(path="/status/404"))
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            response.raise_for_status()
        error = exc_info.value
        assert isinstance(error, httpx.HTTPStatusError)
        pickled_error = pickle.dumps(error)
        unpickled_error = pickle.loads(pickled_error)
        # Note that the unpickled error will not be equal to the original error
        # because requests and responses are compared by identity.
        assert str(unpickled_error) == str(error)
        assert unpickled_error.request is not None
        assert unpickled_error.response is not None
