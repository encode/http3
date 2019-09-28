import hashlib
import json
import os

import pytest

from httpx import (
    URL,
    AsyncDispatcher,
    AsyncRequest,
    AsyncResponse,
    CertTypes,
    Client,
    DigestAuth,
    ProtocolError,
    TimeoutTypes,
    VerifyTypes,
)


class MockDispatch(AsyncDispatcher):
    def __init__(self, auth_header: str = "", status_code: int = 200) -> None:
        self.auth_header = auth_header
        self.status_code = status_code

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        headers = [("www-authenticate", self.auth_header)] if self.auth_header else []
        body = json.dumps({"auth": request.headers.get("Authorization")}).encode()
        return AsyncResponse(
            self.status_code, headers=headers, content=body, request=request
        )


class MockDigestAuthDispatch(AsyncDispatcher):
    def __init__(
        self,
        algorithm: str = "SHA-256",
        send_response_after_attempt: int = 1,
        qop: str = "auth",
        regenerate_nonce: bool = True,
    ) -> None:
        self.algorithm = algorithm
        self.send_response_after_attempt = send_response_after_attempt
        self.qop = qop
        self._regenerate_nonce = regenerate_nonce
        self._response_count = 0

    async def send(
        self,
        request: AsyncRequest,
        verify: VerifyTypes = None,
        cert: CertTypes = None,
        timeout: TimeoutTypes = None,
    ) -> AsyncResponse:
        if self._response_count < self.send_response_after_attempt:
            return self.challenge_send(request)

        body = json.dumps({"auth": request.headers.get("Authorization")}).encode()
        return AsyncResponse(200, content=body, request=request)

    def challenge_send(self, request: AsyncRequest) -> AsyncResponse:
        self._response_count += 1
        nonce = (
            hashlib.sha256(os.urandom(8)).hexdigest()
            if self._regenerate_nonce
            else "ee96edced2a0b43e4869e96ebe27563f369c1205a049d06419bb51d8aeddf3d3"
        )
        challenge_data = {
            "nonce": nonce,
            "qop": self.qop,
            "opaque": (
                "ee6378f3ee14ebfd2fff54b70a91a7c9390518047f242ab2271380db0e14bda1"
            ),
            "algorithm": self.algorithm,
            "stale": "FALSE",
        }
        challenge_str = ", ".join(
            '{}="{}"'.format(key, value)
            for key, value in challenge_data.items()
            if value
        )

        headers = [
            ("www-authenticate", 'Digest realm="httpx@example.org", ' + challenge_str)
        ]
        return AsyncResponse(401, headers=headers, content=b"", request=request)


def test_basic_auth():
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


def test_basic_auth_in_url():
    url = "https://tomchristie:password123@example.org/"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


def test_basic_auth_on_session():
    url = "https://example.org/"
    auth = ("tomchristie", "password123")

    with Client(dispatch=MockDispatch(), auth=auth) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {"auth": "Basic dG9tY2hyaXN0aWU6cGFzc3dvcmQxMjM="}


def test_custom_auth():
    url = "https://example.org/"

    def auth(request):
        request.headers["Authorization"] = "Token 123"
        return request

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": "Token 123"}


def test_netrc_auth():
    os.environ["NETRC"] = "tests/.netrc"
    url = "http://netrcexample.org"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }


def test_trust_env_auth():
    os.environ["NETRC"] = "tests/.netrc"
    url = "http://netrcexample.org"

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, trust_env=False)

    assert response.status_code == 200
    assert response.json() == {"auth": None}

    with Client(dispatch=MockDispatch(), trust_env=False) as client:
        response = client.get(url, trust_env=True)

    assert response.status_code == 200
    assert response.json() == {
        "auth": "Basic ZXhhbXBsZS11c2VybmFtZTpleGFtcGxlLXBhc3N3b3Jk"
    }


def test_auth_hidden_url():
    url = "http://example-username:example-password@example.org/"
    expected = "URL('http://example-username:[secure]@example.org/')"
    assert url == URL(url)
    assert expected == repr(URL(url))


def test_auth_hidden_header():
    url = "https://example.org/"
    auth = ("example-username", "example-password")

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert "'authorization': '[secure]'" in str(response.request.headers)


def test_auth_invalid_type():
    url = "https://example.org/"
    with Client(dispatch=MockDispatch(), auth="not a tuple, not a callable") as client:
        with pytest.raises(TypeError):
            client.get(url)


def test_digest_auth_returns_no_auth_if_no_digest_header_in_response():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDispatch()) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": None}


def test_digest_auth_200_response_including_digest_auth_header_is_returned_as_is():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")
    auth_header = 'Digest realm="realm@host.com",qop="auth",nonce="abc",opaque="xyz"'

    with Client(
        dispatch=MockDispatch(auth_header=auth_header, status_code=200)
    ) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    assert response.json() == {"auth": None}


def test_digest_auth_401_response_without_digest_auth_header_is_returned_as_is():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDispatch(auth_header="", status_code=401)) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 401
    assert response.json() == {"auth": None}


@pytest.mark.parametrize(
    "algorithm,expected_hash_length,expected_response_length",
    [
        ("MD5", 64, 32),
        ("MD5-SESS", 64, 32),
        ("SHA", 64, 40),
        ("SHA-SESS", 64, 40),
        ("SHA-256", 64, 64),
        ("SHA-256-SESS", 64, 64),
        ("SHA-512", 64, 128),
        ("SHA-512-SESS", 64, 128),
    ],
)
def test_digest_auth(algorithm, expected_hash_length, expected_response_length):
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDigestAuthDispatch(algorithm=algorithm)) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    auth = response.json()["auth"]
    assert auth.startswith("Digest ")

    response_fields = [field.strip() for field in auth[auth.find(" ") :].split(",")]
    digest_data = dict(field.split("=") for field in response_fields)

    assert digest_data["username"] == '"tomchristie"'
    assert digest_data["realm"] == '"httpx@example.org"'
    assert "nonce" in digest_data
    assert digest_data["uri"] == '"/"'
    assert len(digest_data["response"]) == expected_response_length + 2  # extra quotes
    assert len(digest_data["opaque"]) == expected_hash_length + 2
    assert digest_data["algorithm"] == algorithm
    assert digest_data["qop"] == "auth"
    assert digest_data["nc"] == "00000001"
    assert len(digest_data["cnonce"]) == 16 + 2


def test_digest_auth_no_specified_qop():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDigestAuthDispatch(qop=None)) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 200
    auth = response.json()["auth"]
    assert auth.startswith("Digest ")

    response_fields = [field.strip() for field in auth[auth.find(" ") :].split(",")]
    digest_data = dict(field.split("=") for field in response_fields)

    assert "qop" not in digest_data
    assert "nc" not in digest_data
    assert "cnonce" not in digest_data
    assert digest_data["username"] == '"tomchristie"'
    assert digest_data["realm"] == '"httpx@example.org"'
    assert len(digest_data["nonce"]) == 64 + 2  # extra quotes
    assert digest_data["uri"] == '"/"'
    assert len(digest_data["response"]) == 64 + 2
    assert len(digest_data["opaque"]) == 64 + 2
    assert digest_data["algorithm"] == "SHA-256"


@pytest.mark.parametrize("qop", ("auth, auth-int", "auth,auth-int", "unknown,auth"))
def test_digest_auth_qop_including_spaces_and_auth_returns_auth(qop: str):
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with Client(dispatch=MockDigestAuthDispatch(qop=qop)) as client:
        client.get(url, auth=auth)


def test_digest_auth_qop_auth_int_not_implemented():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with pytest.raises(NotImplementedError):
        with Client(dispatch=MockDigestAuthDispatch(qop="auth-int")) as client:
            client.get(url, auth=auth)


def test_digest_auth_qop_must_be_auth_or_auth_int():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with pytest.raises(ProtocolError):
        with Client(dispatch=MockDigestAuthDispatch(qop="not-auth")) as client:
            client.get(url, auth=auth)


def test_digest_auth_incorrect_credentials():
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with Client(
        dispatch=MockDigestAuthDispatch(send_response_after_attempt=2)
    ) as client:
        response = client.get(url, auth=auth)

    assert response.status_code == 401


@pytest.mark.parametrize(
    "auth_header",
    [
        'Digest realm="httpx@example.org", qop="auth"',  # missing fields
        'realm="httpx@example.org", qop="auth"',  # not starting with Digest
        'DigestZ realm="httpx@example.org", qop="auth"'
        'qop="auth,auth-int",nonce="abc",opaque="xyz"',
        'Digest realm="httpx@example.org", qop="auth,au',  # malformed fields list
    ],
)
def test_digest_auth_raises_protocol_error_on_malformed_header(auth_header: str):
    url = "https://example.org/"
    auth = DigestAuth(username="tomchristie", password="password123")

    with pytest.raises(ProtocolError):
        with Client(
            dispatch=MockDispatch(auth_header=auth_header, status_code=401)
        ) as client:
            client.get(url, auth=auth)
