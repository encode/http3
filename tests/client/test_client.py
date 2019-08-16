import pytest

import httpx


@pytest.mark.usefixtures("server")
def test_get(backend):
    url = "http://127.0.0.1:8000/"
    with httpx.Client(backend=backend) as http:
        response = http.get(url)
    assert response.status_code == 200
    assert response.url == httpx.URL(url)
    assert response.content == b"Hello, world!"
    assert response.text == "Hello, world!"
    assert response.protocol == "HTTP/1.1"
    assert response.encoding == "iso-8859-1"
    assert response.request.url == httpx.URL(url)
    assert response.headers
    assert response.is_redirect is False
    assert repr(response) == "<Response [200 OK]>"


@pytest.mark.usefixtures("server")
def test_post(backend):
    with httpx.Client(backend=backend) as http:
        response = http.post("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_post_json(backend):
    with httpx.Client(backend=backend) as http:
        response = http.post("http://127.0.0.1:8000/", json={"text": "Hello, world!"})
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_stream_response(backend):
    with httpx.Client(backend=backend) as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    content = response.read()
    assert content == b"Hello, world!"


@pytest.mark.usefixtures("server")
def test_stream_iterator(backend):
    with httpx.Client(backend=backend) as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.stream():
        body += chunk
    assert body == b"Hello, world!"


@pytest.mark.usefixtures("server")
def test_raw_iterator(backend):
    with httpx.Client(backend=backend) as http:
        response = http.get("http://127.0.0.1:8000/", stream=True)
    assert response.status_code == 200
    body = b""
    for chunk in response.raw():
        body += chunk
    assert body == b"Hello, world!"
    response.close()  # TODO: should Response be available as context managers?


@pytest.mark.usefixtures("server")
def test_raise_for_status(backend):
    with httpx.Client(backend=backend) as client:
        for status_code in (200, 400, 404, 500, 505):
            response = client.request(
                "GET", "http://127.0.0.1:8000/status/{}".format(status_code)
            )
            if 400 <= status_code < 600:
                with pytest.raises(httpx.exceptions.HTTPError) as exc_info:
                    response.raise_for_status()
                assert exc_info.value.response == response
            else:
                assert response.raise_for_status() is None


@pytest.mark.usefixtures("server")
def test_options(backend):
    with httpx.Client(backend=backend) as http:
        response = http.options("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_head(backend):
    with httpx.Client(backend=backend) as http:
        response = http.head("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_put(backend):
    with httpx.Client(backend=backend) as http:
        response = http.put("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_patch(backend):
    with httpx.Client(backend=backend) as http:
        response = http.patch("http://127.0.0.1:8000/", data=b"Hello, world!")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_delete(backend):
    with httpx.Client(backend=backend) as http:
        response = http.delete("http://127.0.0.1:8000/")
    assert response.status_code == 200
    assert response.reason_phrase == "OK"


@pytest.mark.usefixtures("server")
def test_base_url(backend):
    base_url = "http://127.0.0.1:8000/"
    with httpx.Client(base_url=base_url, backend=backend) as http:
        response = http.get("/")
    assert response.status_code == 200
    assert str(response.url) == base_url


def test_merge_url():
    client = httpx.Client(base_url="https://www.paypal.com/")
    url = client.merge_url("http://www.paypal.com")

    assert url.scheme == "https"
    assert url.is_ssl
