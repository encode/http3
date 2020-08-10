import hashlib
import os
import re
import time
import typing
from base64 import b64encode
from urllib.request import parse_http_list

from ._exceptions import ProtocolError, RequestBodyUnavailable
from ._models import Request, Response
from ._utils import to_bytes, to_str, unquote


class Auth:
    """
    Base class for all authentication schemes.

    To implement a custom authentication scheme, subclass `Auth` and override
    the `.auth_flow()` method.
    """

    requires_request_body = False
    requires_response_body = False

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        """
        Execute the authentication flow.

        To dispatch a request, `yield` it:

        ```
        yield request
        ```

        The client will `.send()` the response back into the flow generator. You can
        access it like so:

        ```
        response = yield request
        ```

        A `return` (or reaching the end of the generator) will result in the
        client returning the last response obtained from the server.

        You can dispatch as many requests as is necessary.
        """
        yield request


class FunctionAuth(Auth):
    """
    Allows the 'auth' argument to be passed as a simple callable function,
    that takes the request, and returns a new, modified request.
    """

    def __init__(self, func: typing.Callable[[Request], Request]) -> None:
        self._func = func

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        yield self._func(request)


class BasicAuth(Auth):
    """
    Allows the 'auth' argument to be passed as a (username, password) pair,
    and uses HTTP Basic authentication.
    """

    def __init__(
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ):
        self._auth_header = self._build_auth_header(username, password)

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        request.headers["Authorization"] = self._auth_header
        yield request

    @staticmethod
    def _build_auth_header(
        username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> str:
        userpass = b":".join((to_bytes(username), to_bytes(password)))
        token = b64encode(userpass).decode()
        return f"Basic {token}"


class DigestAuth(Auth):
    _ALGORITHM_TO_HASH_FUNCTION: typing.Dict[str, typing.Callable] = {
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
        self, username: typing.Union[str, bytes], password: typing.Union[str, bytes]
    ) -> None:
        self._username = to_bytes(username)
        self._password = to_bytes(password)

    def auth_flow(self, request: Request) -> typing.Generator[Request, Response, None]:
        if not request.stream.can_replay():
            raise RequestBodyUnavailable(
                "Cannot use digest auth with streaming requests that are unable "
                "to replay the request body if a second request is required.",
                request=request,
            )

        response = yield request

        if response.status_code != 401 or "www-authenticate" not in response.headers:
            # If the response is not a 401 WWW-Authenticate, then we don't
            # need to build an authenticated request.
            return

        challenge = self._parse_challenge(request, response)
        request.headers["Authorization"] = self._build_auth_header(request, challenge)
        yield request

    @staticmethod
    def _parse_challenge(
        request: Request, response: Response
    ) -> "_DigestAuthChallenge":
        """
        Returns a challenge from a Digest WWW-Authenticate header.
        These take the form of:
        `Digest realm="realm@host.com",qop="auth,auth-int",nonce="abc",opaque="xyz"`
        """
        header = response.headers["www-authenticate"]

        scheme, _, fields = header.partition(" ")
        if scheme.lower() != "digest":
            message = "Header does not start with 'Digest'"
            raise ProtocolError(message, request=request)

        header_dict: typing.Dict[str, str] = {}
        for field in parse_http_list(fields):
            key, value = field.strip().split("=", 1)
            header_dict[key] = unquote(value)

        try:
            realm = header_dict["realm"].encode()
            nonce = header_dict["nonce"].encode()
            qop = header_dict["qop"].encode() if "qop" in header_dict else None
            opaque = header_dict["opaque"].encode() if "opaque" in header_dict else None
            algorithm = header_dict.get("algorithm", "MD5")
            return _DigestAuthChallenge(
                realm=realm, nonce=nonce, qop=qop, opaque=opaque, algorithm=algorithm
            )
        except KeyError as exc:
            message = "Malformed Digest WWW-Authenticate header"
            raise ProtocolError(message, request=request) from exc

    def _build_auth_header(
        self, request: Request, challenge: "_DigestAuthChallenge"
    ) -> str:
        hash_func = self._ALGORITHM_TO_HASH_FUNCTION[challenge.algorithm]

        def digest(data: bytes) -> bytes:
            return hash_func(data).hexdigest().encode()

        A1 = b":".join((self._username, challenge.realm, self._password))

        path = request.url.full_path.encode("utf-8")
        A2 = b":".join((request.method.encode(), path))
        # TODO: implement auth-int
        HA2 = digest(A2)

        nonce_count = 1  # TODO: implement nonce counting
        nc_value = b"%08x" % nonce_count
        cnonce = self._get_client_nonce(nonce_count, challenge.nonce)

        HA1 = digest(A1)
        if challenge.algorithm.lower().endswith("-sess"):
            HA1 = digest(b":".join((HA1, challenge.nonce, cnonce)))

        qop = self._resolve_qop(challenge.qop, request=request)
        if qop is None:
            digest_data = [HA1, challenge.nonce, HA2]
        else:
            digest_data = [challenge.nonce, nc_value, cnonce, qop, HA2]
        key_digest = b":".join(digest_data)

        format_args = {
            "username": self._username,
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

    @staticmethod
    def _get_client_nonce(nonce_count: int, nonce: bytes) -> bytes:
        s = str(nonce_count).encode()
        s += nonce
        s += time.ctime().encode()
        s += os.urandom(8)

        return hashlib.sha1(s).hexdigest()[:16].encode()

    @staticmethod
    def _get_header_value(header_fields: typing.Dict[str, bytes]) -> str:
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

    def _resolve_qop(
        self, qop: typing.Optional[bytes], request: Request
    ) -> typing.Optional[bytes]:
        if qop is None:
            return None
        qops = re.split(b", ?", qop)
        if b"auth" in qops:
            return b"auth"

        if qops == [b"auth-int"]:
            raise NotImplementedError("Digest auth-int support is not yet implemented")

        message = f'Unexpected qop value "{qop!r}" in digest auth'
        raise ProtocolError(message, request=request)


class _DigestAuthChallenge:
    def __init__(
        self,
        realm: bytes,
        nonce: bytes,
        algorithm: str,
        opaque: typing.Optional[bytes] = None,
        qop: typing.Optional[bytes] = None,
    ) -> None:
        self.realm = realm
        self.nonce = nonce
        self.algorithm = algorithm
        self.opaque = opaque
        self.qop = qop
