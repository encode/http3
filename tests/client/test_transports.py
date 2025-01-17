import pytest

from httpx import AsyncHTTPTransport, HTTPTransport
from httpx._transports.default import _DEFAULT_TRUST_ENV, _DEFAULT_VERIFY

DIFFERENT_VERIFY = {"verify": not _DEFAULT_VERIFY}
DIFFERENT_CERT_ENV = {"cert": ()}
DIFFERENT_TRUST_ENV = {"trust_env": not _DEFAULT_TRUST_ENV}


@pytest.mark.parametrize("transport", [HTTPTransport, AsyncHTTPTransport])
def test_default_ssl_config_cached(transport):
    transport_1 = transport()
    transport_2 = transport()
    assert transport_1._pool._ssl_context is not None
    assert transport_2._pool._ssl_context is not None

    assert transport_1._pool._ssl_context is transport_2._pool._ssl_context


@pytest.mark.parametrize("transport", [HTTPTransport, AsyncHTTPTransport])
@pytest.mark.parametrize(
    ("kwargs_1", "kwargs_2"),
    [
        ({}, DIFFERENT_VERIFY),
        (DIFFERENT_VERIFY, {}),
        (DIFFERENT_VERIFY, DIFFERENT_VERIFY),
        ({}, DIFFERENT_CERT_ENV),
        (DIFFERENT_CERT_ENV, {}),
        (DIFFERENT_CERT_ENV, DIFFERENT_CERT_ENV),
        ({}, DIFFERENT_TRUST_ENV),
        (DIFFERENT_TRUST_ENV, {}),
        (DIFFERENT_TRUST_ENV, DIFFERENT_TRUST_ENV),
    ],
)
def test_non_default_ssl_config_not_cached(transport, kwargs_1, kwargs_2):
    transport_1 = transport(**kwargs_1)
    transport_2 = transport(**kwargs_2)
    assert transport_1._pool._ssl_context is not None
    assert transport_2._pool._ssl_context is not None

    assert transport_1._pool._ssl_context is not transport_2._pool._ssl_context
