import hashlib
import os
import re
import time
import typing
from base64 import b64encode
from collections import defaultdict
from urllib.request import parse_http_list

from ..exceptions import ProtocolError
from ..models import AsyncRequest, AsyncResponse, StatusCode
from ..utils import to_bytes, to_str, unquote
from .base import BaseMiddleware


class BasicAuth(BaseMiddleware):
    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        username = to_bytes(username)
        password = to_bytes(password)
        userpass = b":".join((username, password))
        token = b64encode(userpass).decode().strip()

        self.authorization_header = f"Basic {token}"

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request.headers["Authorization"] = self.authorization_header
        return await get_response(request)


class CustomAuth(BaseMiddleware):
    def __init__(self, auth: typing.Callable[[AsyncRequest], AsyncRequest]):
        self.auth = auth

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request = self.auth(request)
        return await get_response(request)


class DigestAuth(BaseMiddleware):
    per_nonce_count: typing.Dict[bytes, int] = defaultdict(lambda: 0)

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self.username = to_bytes(username)
        self.password = to_bytes(password)

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        request_middleware = _RequestDigestAuth(
            username=self.username,
            password=self.password,
            per_nonce_count=self.per_nonce_count,
        )
        return await request_middleware(request=request, get_response=get_response)


class _RequestDigestAuth(BaseMiddleware):
    ALGORITHM_TO_HASH_FUNCTION: typing.Dict[str, typing.Callable] = {
        "MD5": hashlib.md5,
        "MD5-SESS": hashlib.md5,
        "SHA": hashlib.sha1,
        "SHA-SESS": hashlib.sha1,
        "SHA-256": hashlib.sha256,
        "SHA-256-SESS": hashlib.sha256,
        "SHA-512": hashlib.sha512,
        "SHA-512-SESS": hashlib.sha512,
    }

    def __init__(
        self, username: bytes, password: bytes, per_nonce_count: typing.Dict[bytes, int]
    ) -> None:
        self.username = username
        self.password = password
        self.per_nonce_count = per_nonce_count
        self.num_401_responses = 0

    async def __call__(
        self, request: AsyncRequest, get_response: typing.Callable
    ) -> AsyncResponse:
        response = await get_response(request)
        if not (
            StatusCode.is_client_error(response.status_code)
            and "www-authenticate" in response.headers
        ):
            self.num_401_responses = 0
            return response

        header = response.headers["www-authenticate"]
        try:
            challenge = DigestAuthChallenge.from_header(header)
        except ValueError:
            raise ProtocolError("Malformed Digest authentication header")

        if self._previous_auth_failed(challenge):
            return response

        request.headers["Authorization"] = self._build_auth_header(request, challenge)
        return await self(request, get_response)

    def _previous_auth_failed(self, challenge: "DigestAuthChallenge") -> bool:
        """Returns whether the previous auth failed.

        This is fairly subtle as the server may return a 401 with the *same* nonce that
        that of our first attempt. If it is different, however, we know the server has
        rejected our credentials.
        """
        self.num_401_responses += 1

        return (
            challenge.nonce not in self.per_nonce_count and self.num_401_responses > 1
        )

    def _build_auth_header(
        self, request: AsyncRequest, challenge: "DigestAuthChallenge"
    ) -> str:
        hash_func = self.ALGORITHM_TO_HASH_FUNCTION[challenge.algorithm]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode()

        A1 = b":".join((self.username, challenge.realm, self.password))

        path = request.url.full_path.encode("utf-8")
        A2 = b":".join((request.method.encode(), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        nonce_count, nc_value = self._get_nonce_count(challenge.nonce)
        cnonce = self._get_client_nonce(nonce_count, challenge.nonce)

        HA1 = digest(A1)
        if challenge.algorithm.lower().endswith("-sess"):
            HA1 = digest(b":".join((HA1, challenge.nonce, cnonce)))

        qop = self._resolve_qop(challenge.qop)
        if qop is None:
            digest_data = [HA1, challenge.nonce, HA2]
        else:
            digest_data = [challenge.nonce, nc_value, cnonce, qop, HA2]
        key_digest = b":".join(digest_data)

        format_args = {
            "username": self.username,
            "realm": challenge.realm,
            "nonce": challenge.nonce,
            "uri": path,
            "response": digest(b":".join((HA1, key_digest))),
            "algorithm": challenge.algorithm.encode(),
        }
        if challenge.opaque:
            format_args["opaque"] = challenge.opaque
        if qop:
            format_args["qop"] = b"auth"
            format_args["nc"] = nc_value
            format_args["cnonce"] = cnonce

        return "Digest " + self._get_header_value(format_args)

    def _get_client_nonce(self, nonce_count: int, nonce: bytes) -> bytes:
        s = str(nonce_count).encode()
        s += nonce
        s += time.ctime().encode()
        s += os.urandom(8)

        return hashlib.sha1(s).hexdigest()[:16].encode()

    def _get_nonce_count(self, nonce: bytes) -> typing.Tuple[int, bytes]:
        """Returns the number of requests made with the same server provided
        nonce value along with its 8-digit hex representation."""
        self.per_nonce_count[nonce] += 1
        return self.per_nonce_count[nonce], b"%08x" % self.per_nonce_count[nonce]

    def _get_header_value(self, header_fields: typing.Dict[str, bytes]) -> str:
        NON_QUOTED_FIELDS = ("algorithm", "qop", "nc")
        QUOTED_TEMPLATE = '{}="{}"'
        NON_QUOTED_TEMPLATE = "{}={}"

        header_value = ""
        for i, (field, value) in enumerate(header_fields.items()):
            if i > 0:
                header_value += ", "
            template = (
                QUOTED_TEMPLATE
                if field not in NON_QUOTED_FIELDS
                else NON_QUOTED_TEMPLATE
            )
            header_value += template.format(field, to_str(value))

        return header_value

    def _resolve_qop(self, qop: typing.Optional[bytes]) -> typing.Optional[bytes]:
        if qop is None:
            return None
        qops = re.split(b", ?", qop)
        if b"auth" in qops:
            return b"auth"

        if qops == [b"auth-int"]:
            raise NotImplementedError("Digest auth-int support is not yet implemented")

        raise ProtocolError(f'Unexpected qop value "{qop!r}" in digest auth')


class DigestAuthChallenge:
    def __init__(
        self,
        realm: bytes,
        nonce: bytes,
        algorithm: str = None,
        opaque: typing.Optional[bytes] = None,
        qop: typing.Optional[bytes] = None,
    ) -> None:
        self.realm = realm
        self.nonce = nonce
        self.algorithm = algorithm or "MD5"
        self.opaque = opaque
        self.qop = qop

    @classmethod
    def from_header(cls, header: str) -> "DigestAuthChallenge":
        """Returns a challenge from a Digest WWW-Authenticate header.

        These take the form of:
        `Digest realm="realm@host.com",qop="auth,auth-int",nonce="abc",opaque="xyz"`
        """
        scheme, _, fields = header.partition(" ")
        if scheme.lower() != "digest":
            raise ValueError("Header does not start with 'Digest'")

        header_dict: typing.Dict[str, str] = {}
        for field in parse_http_list(fields):
            key, value = field.strip().split("=")
            header_dict[key] = unquote(value)

        try:
            return cls.from_header_dict(header_dict)
        except KeyError as exc:
            raise ValueError("Malformed Digest WWW-Authenticate header") from exc

    @classmethod
    def from_header_dict(cls, header_dict: dict) -> "DigestAuthChallenge":
        realm = header_dict["realm"].encode()
        nonce = header_dict["nonce"].encode()
        qop = header_dict["qop"].encode() if "qop" in header_dict else None
        opaque = header_dict["opaque"].encode() if "opaque" in header_dict else None
        algorithm = header_dict.get("algorithm")
        return cls(
            realm=realm, nonce=nonce, qop=qop, opaque=opaque, algorithm=algorithm
        )
