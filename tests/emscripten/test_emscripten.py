from typing import Any

import pytest

import httpx

# only run these tests if pytest_pyodide is installed
# so we don't break non-emscripten pytest running
pytest_pyodide = pytest.importorskip("pytest_pyodide")

# make our ssl certificates work in chrome
pyodide_config = pytest_pyodide.config.get_global_config()
pyodide_config.set_flags(
    "chrome", ["ignore-certificate-errors"] + pyodide_config.get_flags("chrome")
)


def test_get(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    pyodide_coverage.run_with_httpx(
        f"""
    import httpx
    response = httpx.get('{server_url}')
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    assert response.text == "Hello, world!"
    assert response.http_version == "HTTP/1.1"
    """,
        wheel_url,
    )


def test_post_http(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    pyodide_coverage.run_with_httpx(
        f"""
    import httpx
    response = httpx.post('{server_url}', content=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"
    """,
        wheel_url,
    )


def test_async_get(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    pyodide_coverage.run_with_httpx(
        f"""
        import httpx
        url = '{server_url}'
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            assert response.status_code == 200
            assert response.text == "Hello, world!"
            assert response.http_version == "HTTP/1.1"
            assert response.headers
            assert repr(response) == "<Response [200 OK]>"
    """,
        wheel_url,
    )


def test_async_get_timeout(
    server_url: httpx.URL,
    wheel_url: httpx.URL,
    pyodide_coverage: Any,
    request: pytest.FixtureRequest,
) -> None:
    # test timeout on https and http
    timeout_url = server_url.copy_with(
        path="/slow_response", query=request.node.callspec.id.encode("UTF-8")
    )
    pyodide_coverage.run_with_httpx(
        f"""
        import httpx
        import pytest
        url = '{timeout_url}'
        with pytest.raises(httpx.TimeoutException):
            async with httpx.AsyncClient() as client:
                response = await client.get(url,timeout=0.1)
                print(response.text)
    """,
        wheel_url,
    )


def test_sync_get_timeout(
    server_url: httpx.URL,
    wheel_url: httpx.URL,
    pyodide_coverage: Any,
    has_jspi: bool,
    request: pytest.FixtureRequest,
) -> None:
    # test timeout on https and http
    if not has_jspi:
        # if we are using XMLHttpRequest in a main browser thread then
        # this will never timeout, or at least it will use the default
        # browser timeout which is VERY long!
        pytest.skip()
    timeout_url = server_url.copy_with(
        path="/slow_response", query=request.node.callspec.id.encode("UTF-8")
    )
    pyodide_coverage.run_with_httpx(
        f"""
        import httpx
        import pytest
        url = '{timeout_url}'
        with pytest.raises(httpx.TimeoutException):
            response = httpx.get(url,timeout=0.1)
            print(response.text)
    """,
        wheel_url,
    )


def test_sync_get_timeout_worker(
    server_url: httpx.URL,
    wheel_url: httpx.URL,
    pyodide_coverage: Any,
    request: pytest.FixtureRequest,
) -> None:
    # test timeout on https and http
    # this should timeout in 0.1 seconds
    # (and shouldn't hit cache because of query string)
    timeout_url = server_url.copy_with(
        path="/slow_response", query=request.node.callspec.id.encode("UTF-8")
    )
    pyodide_coverage.run_webworker_with_httpx(
        f"""
        import httpx
        import pytest
        url = '{timeout_url}'
        with pytest.raises(httpx.TimeoutException):
            response = httpx.get(url,timeout=0.1)
            print(response.text)

    """,
        wheel_url,
    )


def test_get_worker(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    pyodide_coverage.run_webworker_with_httpx(
        f"""
        import httpx
        response = httpx.get('{server_url}')
        assert response.status_code == 200
        assert response.reason_phrase == "OK"
        assert response.text == "Hello, world!"
        1
        """,
        wheel_url,
    )


def test_async_get_error(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    # test timeout on https and http
    # 255.255.255.255 should always return an error
    error_url = str(server_url).split(":")[0] + "://255.255.255.255/"
    pyodide_coverage.run_with_httpx(
        f"""
        import httpx
        import pytest
        url = '{error_url}'
        with pytest.raises(httpx.ConnectError):
            response = httpx.get(url)        
    """,
        wheel_url,
    )


def test_sync_get_error(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    # test timeout on https and http
    # 255.255.255.255 should always return an error
    error_url = str(server_url).split(":")[0] + "://255.255.255.255/"
    pyodide_coverage.run_with_httpx(
        f"""
        import httpx
        import pytest
        url = '{error_url}'
        with pytest.raises(httpx.ConnectError):
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(url)
                print(response.text)
    """,
        wheel_url,
    )


def test_async_post_json(
    server_url: httpx.URL, wheel_url: httpx.URL, pyodide_coverage: Any
) -> None:
    pyodide_coverage.run_with_httpx(
        f"""
        import httpx
        url     = '{server_url}'
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={{"text": "Hello, world!"}})
            assert response.status_code == 200
    """,
        wheel_url,
    )
