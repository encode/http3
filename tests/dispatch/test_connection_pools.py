import pytest

import httpx
from httpx.dispatch.connection_pool import ConnectionPool


@pytest.mark.usefixtures("async_environment")
async def test_keepalive_connections(server):
    """
    Connections should default to staying in a keep-alive state.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.usefixtures("async_environment")
async def test_keepalive_timeout(server):
    """
    Keep-alive connections should timeout.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        http.next_keepalive_check = 0.0
        await http.check_keepalive_expiry()

        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

    async with ConnectionPool() as http:
        http.KEEP_ALIVE_EXPIRY = 0.0

        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        http.next_keepalive_check = 0.0
        await http.check_keepalive_expiry()

        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0


@pytest.mark.usefixtures("async_environment")
async def test_differing_connection_keys(server):
    """
    Connections to differing connection keys should result in multiple connections.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://localhost:8000/")
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 2


@pytest.mark.usefixtures("async_environment")
async def test_soft_limit(server):
    """
    The soft_limit config should limit the maximum number of keep-alive connections.
    """
    pool_limits = httpx.PoolLimits(soft_limit=1)

    async with ConnectionPool(pool_limits=pool_limits) as http:
        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1

        response = await http.request("GET", "http://localhost:8000/")
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.usefixtures("async_environment")
async def test_streaming_response_holds_connection(server):
    """
    A streaming request should hold the connection open until the response is read.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 0

        await response.aread()

        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.usefixtures("async_environment")
async def test_multiple_concurrent_connections(server):
    """
    Multiple conncurrent requests should open multiple conncurrent connections.
    """
    async with ConnectionPool() as http:
        response_a = await http.request("GET", server.url)
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 0

        response_b = await http.request("GET", server.url)
        assert len(http.active_connections) == 2
        assert len(http.keepalive_connections) == 0

        await response_b.aread()
        assert len(http.active_connections) == 1
        assert len(http.keepalive_connections) == 1

        await response_a.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 2


@pytest.mark.usefixtures("async_environment")
async def test_close_connections(server):
    """
    Using a `Connection: close` header should close the connection.
    """
    headers = [(b"connection", b"close")]
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url, headers=headers)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0


@pytest.mark.usefixtures("async_environment")
async def test_standard_response_close(server):
    """
    A standard close should keep the connection open.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aread()
        await response.aclose()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.usefixtures("async_environment")
async def test_premature_response_close(server):
    """
    A premature close should close the connection.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aclose()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 0


@pytest.mark.usefixtures("async_environment")
async def test_keepalive_connection_closed_by_server_is_reestablished(server):
    """
    Upon keep-alive connection closed by remote a new connection
    should be reestablished.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aread()

        # Shutdown the server to close the keep-alive connection
        await server.restart()

        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.usefixtures("async_environment")
async def test_keepalive_http2_connection_closed_by_server_is_reestablished(server):
    """
    Upon keep-alive connection closed by remote a new connection
    should be reestablished.
    """
    async with ConnectionPool() as http:
        response = await http.request("GET", server.url)
        await response.aread()

        # Shutdown the server to close the keep-alive connection
        await server.restart()

        response = await http.request("GET", server.url)
        await response.aread()
        assert len(http.active_connections) == 0
        assert len(http.keepalive_connections) == 1


@pytest.mark.usefixtures("async_environment")
async def test_connection_closed_free_semaphore_on_acquire(server):
    """
    Verify that max_connections semaphore is released
    properly on a disconnected connection.
    """
    async with ConnectionPool(pool_limits=httpx.PoolLimits(hard_limit=1)) as http:
        response = await http.request("GET", server.url)
        await response.aread()

        # Close the connection so we're forced to recycle it
        await server.restart()

        response = await http.request("GET", server.url)
        assert response.status_code == 200


@pytest.mark.usefixtures("async_environment")
async def test_connection_pool_closed_close_keepalive_and_free_semaphore(server):
    """
    Closing the connection pool should close remaining keepalive connections and
    release the max_connections semaphore.
    """
    http = ConnectionPool(pool_limits=httpx.PoolLimits(hard_limit=1))

    async with http:
        response = await http.request("GET", server.url)
        await response.aread()
        assert response.status_code == 200
        assert len(http.keepalive_connections) == 1

    assert len(http.keepalive_connections) == 0

    # Perform a second round of requests to make sure the max_connections semaphore
    # was released properly.

    async with http:
        response = await http.request("GET", server.url)
        await response.aread()
        assert response.status_code == 200
