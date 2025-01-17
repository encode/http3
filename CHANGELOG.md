# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 0.28.1 (6th December, 2024)

* Fix SSL case where `verify=False` together with client side certificates.
 
## 0.28.0 (28th November, 2024)

Be aware that the default *JSON request bodies now use a more compact representation*. This is generally considered a prefered style, tho may require updates to test suites.

The 0.28 release includes a limited set of deprecations...

**Deprecations**:

We are working towards a simplified SSL configuration API.

*For users of the standard `verify=True` or `verify=False` cases, or `verify=<ssl_context>` case this should require no changes. The following cases have been deprecated...*

* The `verify` argument as a string argument is now deprecated and will raise warnings.
* The `cert` argument is now deprecated and will raise warnings.

Our revised [SSL documentation](docs/advanced/ssl.md) covers how to implement the same behaviour with a more constrained API.

**The following changes are also included**:

* The deprecated `proxies` argument has now been removed.
* The deprecated `app` argument has now been removed.
* JSON request bodies use a compact representation. (#3363)
* Review URL percent escape sets, based on WHATWG spec. (#3371, #3373)
* Ensure `certifi` and `httpcore` are only imported if required. (#3377)
* Treat `socks5h` as a valid proxy scheme. (#3178)
* Cleanup `Request()` method signature in line with `client.request()` and `httpx.request()`. (#3378)
* Bugfix: When passing `params={}`, always strictly update rather than merge with an existing querystring. (#3364)

## 0.27.2 (27th August, 2024)

### Fixed

* Reintroduced supposedly-private `URLTypes` shortcut. (#2673)

## 0.27.1 (27th August, 2024)

### Added

* Support for `zstd` content decoding using the python `zstandard` package is added. Installable using `httpx[zstd]`. (#3139)

### Fixed

* Improved error messaging for `InvalidURL` exceptions. (#3250)
* Fix `app` type signature in `ASGITransport`. (#3109)

## 0.27.0 (21st February, 2024)

### Deprecated

* The `app=...` shortcut has been deprecated. Use the explicit style of `transport=httpx.WSGITransport()` or `transport=httpx.ASGITransport()` instead.

### Fixed

* Respect the `http1` argument while configuring proxy transports. (#3023)
* Fix RFC 2069 mode digest authentication. (#3045)

## 0.26.0 (20th December, 2023)

### Added

* The `proxy` argument was added. You should use the `proxy` argument instead of the deprecated `proxies`, or use `mounts=` for more complex configurations. (#2879)

### Deprecated

* The `proxies` argument is now deprecated. It will still continue to work, but it will be removed in the future. (#2879)

### Fixed

* Fix cases of double escaping of URL path components. Allow / as a safe character in the query portion. (#2990)
* Handle `NO_PROXY` envvar cases when a fully qualified URL is supplied as the value. (#2741)
* Allow URLs where username or password contains unescaped '@'. (#2986)
* Ensure ASGI `raw_path` does not include URL query component. (#2999)
* Ensure `Response.iter_text()` cannot yield empty strings. (#2998)

## 0.25.2 (24th November, 2023)

### Added

* Add missing type hints to few `__init__()` methods. (#2938)

## 0.25.1 (3rd November, 2023)

### Added

* Add support for Python 3.12. (#2854)
* Add support for httpcore 1.0 (#2885)

### Fixed

* Raise `ValueError` on `Response.encoding` being set after `Response.text` has been accessed. (#2852)

## 0.25.0 (11th September, 2023)

### Removed

* Drop support for Python 3.7. (#2813)

### Added

* Support HTTPS proxies. (#2845)
* Change the type of `Extensions` from `Mapping[Str, Any]` to `MutableMapping[Str, Any]`. (#2803)
* Add `socket_options` argument to `httpx.HTTPTransport` and `httpx.AsyncHTTPTransport` classes. (#2716)
* The `Response.raise_for_status()` method now returns the response instance. For example: `data = httpx.get('...').raise_for_status().json()`. (#2776)

### Fixed

* Return `500` error response instead of exceptions when `raise_app_exceptions=False` is set on `ASGITransport`. (#2669)
* Ensure all `WSGITransport` environs have a `SERVER_PROTOCOL`. (#2708)
* Always encode forward slashes as `%2F` in query parameters (#2723)
* Use Mozilla documentation instead of `httpstatuses.com` for HTTP error reference (#2768)

## 0.24.1 (17th May, 2023)

### Added

* Provide additional context in some `InvalidURL` exceptions. (#2675)

### Fixed

* Fix optional percent-encoding behaviour. (#2671)
* More robust checking for opening upload files in binary mode. (#2630)
* Properly support IP addresses in `NO_PROXY` environment variable. (#2659)
* Set default file for `NetRCAuth()` to `None` to use the stdlib default. (#2667)
* Set logging request lines to INFO level for async requests, in line with sync requests. (#2656)
* Fix which gen-delims need to be escaped for path/query/fragment components in URL. (#2701)

## 0.24.0 (6th April, 2023)

### Changed

* The logging behaviour has been changed to be more in-line with other standard Python logging usages. We no longer have a custom `TRACE` log level, and we no longer use the `HTTPX_LOG_LEVEL` environment variable to auto-configure logging. We now have a significant amount of `DEBUG` logging available at the network level. Full documentation is available at https://www.python-httpx.org/logging/ (#2547, encode/httpcore#648)
* The `Response.iter_lines()` method now matches the stdlib behaviour and does not include the newline characters. It also resolves a performance issue. (#2423)
* Query parameter encoding switches from using + for spaces and %2F for forward slash, to instead using %20 for spaces and treating forward slash as a safe, unescaped character. This differs from `requests`, but is in line with browser behavior in Chrome, Safari, and Firefox. Both options are RFC valid. (#2543)
* NetRC authentication is no longer automatically handled, but is instead supported by an explicit `httpx.NetRCAuth()` authentication class. See the documentation at https://www.python-httpx.org/advanced/authentication/#netrc-authentication (#2525)

### Removed

* The `rfc3986` dependancy has been removed. (#2252)

## 0.23.3 (4th January, 2023)

### Fixed

* Version 0.23.2 accidentally included stricter type checking on query parameters. This shouldn've have been included in a minor version bump, and is now reverted. (#2523, #2539)

## 0.23.2 (2nd January, 2023)

### Added

* Support digest auth nonce counting to avoid multiple auth requests. (#2463)

### Fixed

* Multipart file uploads where the file length cannot be determine now use chunked transfer encoding, rather than loading the entire file into memory in order to determine the `Content-Length`. (#2382)
* Raise `TypeError` if content is passed a dict-instance. (#2495)
* Partially revert the API breaking change in 0.23.1, which removed `RawURL`. We continue to expose a `url.raw` property which is now a plain named-tuple. This API is still expected to be deprecated, but we will do so with a major version bump. (#2481)

## 0.23.1 (18th November, 2022)

**Note**: The 0.23.1 release should have used a proper version bump, rather than a minor point release.
There are API surface area changes that may affect some users.
See the "Removed" section of these release notes for details.

### Added

* Support for Python 3.11. (#2420)
* Allow setting an explicit multipart boundary in `Content-Type` header. (#2278)
* Allow `tuple` or `list` for multipart values, not just `list`. (#2355)
* Allow `str` content for multipart upload files. (#2400)
* Support connection upgrades. See https://www.encode.io/httpcore/extensions/#upgrade-requests

### Fixed

* Don't drop empty query parameters. (#2354)

### Removed

* Upload files *must* always be opened in binary mode. (#2400)
* Drop `.read`/`.aread` from `SyncByteStream`/`AsyncByteStream`. (#2407)
* Drop `RawURL`. (#2241)

## 0.23.0 (23rd May, 2022)

### Changed

* Drop support for Python 3.6. (#2097)
* Use `utf-8` as the default character set, instead of falling back to `charset-normalizer` for auto-detection. To enable automatic character set detection, see [the documentation](https://www.python-httpx.org/advanced/text-encodings/#using-auto-detection). (#2165)

### Fixed

* Fix `URL.copy_with` for some oddly formed URL cases. (#2185)
* Digest authentication should use case-insensitive comparison for determining which algorithm is being used. (#2204)
* Fix console markup escaping in command line client. (#1866)
* When files are used in multipart upload, ensure we always seek to the start of the file. (#2065)
* Ensure that `iter_bytes` never yields zero-length chunks. (#2068)
* Preserve `Authorization` header for redirects that are to the same origin, but are an `http`-to-`https` upgrade. (#2074)
* When responses have binary output, don't print the output to the console in the command line client. Use output like `<16086 bytes of binary data>` instead. (#2076)
* Fix display of `--proxies` argument in the command line client help. (#2125)
* Close responses when task cancellations occur during stream reading. (#2156)
* Fix type error on accessing `.request` on `HTTPError` exceptions. (#2158)

## 0.22.0 (26th January, 2022)

### Added

* Support for [the SOCKS5 proxy protocol](https://www.python-httpx.org/advanced/proxies/#socks) via [the `socksio` package](https://github.com/sethmlarson/socksio). (#2034)
* Support for custom headers in multipart/form-data requests (#1936)

### Fixed

* Don't perform unreliable close/warning on `__del__` with unclosed clients. (#2026)
* Fix `Headers.update(...)` to correctly handle repeated headers (#2038)

## 0.21.3 (6th January, 2022)

### Fixed

* Fix streaming uploads using `SyncByteStream` or `AsyncByteStream`. Regression in 0.21.2. (#2016)

## 0.21.2 (5th January, 2022)

### Fixed

* HTTP/2 support for tunnelled proxy cases. (#2009)
* Improved the speed of large file uploads. (#1948)

## 0.21.1 (16th November, 2021)

### Fixed

* The `response.url` property is now correctly annotated as `URL`, instead of `Optional[URL]`. (#1940)

## 0.21.0 (15th November, 2021)

The 0.21.0 release integrates against a newly redesigned `httpcore` backend.

Both packages ought to automatically update to the required versions, but if you are
seeing any issues, you should ensure that you have `httpx==0.21.*` and `httpcore==0.14.*` installed.

### Added

* The command-line client will now display connection information when `-v/--verbose` is used.
* The command-line client will now display server certificate information when `-v/--verbose` is used.
* The command-line client is now able to properly detect if the outgoing request
should be formatted as HTTP/1.1 or HTTP/2, based on the result of the HTTP/2 negotiation.

### Removed

* Curio support is no longer currently included. Please get in touch if you require this, so that we can assess priorities.

## 0.20.0 (13th October, 2021)

The 0.20.0 release adds an integrated command-line client, and also includes some
design changes. The most notable of these is that redirect responses are no longer
automatically followed, unless specifically requested.

This design decision prioritises a more explicit approach to redirects, in order
to avoid code that unintentionally issues multiple requests as a result of
misconfigured URLs.

For example, previously a client configured to send requests to `http://api.github.com/`
would end up sending every API request twice, as each request would be redirected to `https://api.github.com/`.

If you do want auto-redirect behaviour, you can enable this either by configuring
the client instance with `Client(follow_redirects=True)`, or on a per-request
basis, with `.get(..., follow_redirects=True)`.

This change is a classic trade-off between convenience and precision, with no "right"
answer. See [discussion #1785](https://github.com/encode/httpx/discussions/1785) for more
context.

The other major design change is an update to the Transport API, which is the low-level
interface against which requests are sent. Previously this interface used only primitive
datastructures, like so...

```python
(status_code, headers, stream, extensions) = transport.handle_request(method, url, headers, stream, extensions)
try
    ...
finally:
    stream.close()
```

Now the interface is much simpler...

```python
response = transport.handle_request(request)
try
    ...
finally:
    response.close()
```

### Changed

* The `allow_redirects` flag is now `follow_redirects` and defaults to `False`.
* The `raise_for_status()` method will now raise an exception for any responses
  except those with 2xx status codes. Previously only 4xx and 5xx status codes
  would result in an exception.
* The low-level transport API changes to the much simpler `response = transport.handle_request(request)`.
* The `client.send()` method no longer accepts a `timeout=...` argument, but the
  `client.build_request()` does. This required by the signature change of the
  Transport API. The request timeout configuration is now stored on the request
  instance, as `request.extensions['timeout']`.

### Added

* Added the `httpx` command-line client.
* Response instances now include `.is_informational`, `.is_success`, `.is_redirect`, `.is_client_error`, and `.is_server_error`
  properties for checking 1xx, 2xx, 3xx, 4xx, and 5xx response types. Note that the behaviour of `.is_redirect` is slightly different in that it now returns True for all 3xx responses, in order to allow for a consistent set of properties onto the different HTTP status code types. The `response.has_redirect_location` location may be used to determine responses with properly formed URL redirects.

### Fixed

* `response.iter_bytes()` no longer raises a ValueError when called on a response with no content. (Pull #1827)
* The `'wsgi.error'` configuration now defaults to `sys.stderr`, and is corrected to be a `TextIO` interface, not a `BytesIO` interface. Additionally, the WSGITransport now accepts a `wsgi_error` configuration. (Pull #1828)
* Follow the WSGI spec by properly closing the iterable returned by the application. (Pull #1830)

## 0.19.0 (19th August, 2021)

### Added

* Add support for `Client(allow_redirects=<bool>)`. (Pull #1790)
* Add automatic character set detection, when no `charset` is included in the response `Content-Type` header. (Pull #1791)

### Changed

* Event hooks are now also called for any additional redirect or auth requests/responses. (Pull #1806)
* Strictly enforce that upload files must be opened in binary mode. (Pull #1736)
* Strictly enforce that client instances can only be opened and closed once, and cannot be re-opened. (Pull #1800)
* Drop `mode` argument from `httpx.Proxy(..., mode=...)`. (Pull #1795)

## 0.18.2 (17th June, 2021)

### Added

* Support for Python 3.10. (Pull #1687)
* Expose `httpx.USE_CLIENT_DEFAULT`, used as the default to `auth` and `timeout` parameters in request methods. (Pull #1634)
* Support [HTTP/2 "prior knowledge"](https://python-hyper.org/projects/hyper-h2/en/v2.3.1/negotiating-http2.html#prior-knowledge), using `httpx.Client(http1=False, http2=True)`. (Pull #1624)

### Fixed

* Clean up some cases where warnings were being issued. (Pull #1687)
* Prefer Content-Length over Transfer-Encoding: chunked for content=<file-like> cases. (Pull #1619)

## 0.18.1 (29th April, 2021)

### Changed

* Update brotli support to use the `brotlicffi` package (Pull #1605)
* Ensure that `Request(..., stream=...)` does not auto-generate any headers on the request instance. (Pull #1607)

### Fixed

* Pass through `timeout=...` in top-level httpx.stream() function. (Pull #1613)
* Map httpcore transport close exceptions to httpx exceptions. (Pull #1606)

## 0.18.0 (27th April, 2021)

The 0.18.x release series formalises our low-level Transport API, introducing the base classes `httpx.BaseTransport` and `httpx.AsyncBaseTransport`.

See the "[Custom transports](https://www.python-httpx.org/advanced/transports/#custom-transports)" documentation and the [`httpx.BaseTransport.handle_request()`](https://github.com/encode/httpx/blob/397aad98fdc8b7580a5fc3e88f1578b4302c6382/httpx/_transports/base.py#L77-L147) docstring for more complete details on implementing custom transports.

Pull request #1522 includes a checklist of differences from the previous `httpcore` transport API, for developers implementing custom transports.

The following API changes have been issuing deprecation warnings since 0.17.0 onwards, and are now fully deprecated...

* You should now use httpx.codes consistently instead of httpx.StatusCodes.
* Use limits=... instead of pool_limits=....
* Use proxies={"http://": ...} instead of proxies={"http": ...} for scheme-specific mounting.

### Changed

* Transport instances now inherit from `httpx.BaseTransport` or `httpx.AsyncBaseTransport`,
  and should implement either the `handle_request` method or `handle_async_request` method. (Pull #1522, #1550)
* The `response.ext` property and `Response(ext=...)` argument are now named `extensions`. (Pull #1522)
* The recommendation to not use `data=<bytes|str|bytes (a)iterator>` in favour of `content=<bytes|str|bytes (a)iterator>` has now been escalated to a deprecation warning. (Pull #1573)
* Drop `Response(on_close=...)` from API, since it was a bit of leaking implementation detail. (Pull #1572)
* When using a client instance, cookies should always be set on the client, rather than on a per-request basis. We prefer enforcing a stricter API here because it provides clearer expectations around cookie persistence, particularly when redirects occur. (Pull #1574)
* The runtime exception `httpx.ResponseClosed` is now named `httpx.StreamClosed`. (#1584)
* The `httpx.QueryParams` model now presents an immutable interface. There is a discussion on [the design and motivation here](https://github.com/encode/httpx/discussions/1599). Use `client.params = client.params.merge(...)` instead of `client.params.update(...)`. The basic query manipulation methods are `query.set(...)`, `query.add(...)`, and `query.remove()`. (#1600)

### Added

* The `Request` and `Response` classes can now be serialized using pickle. (#1579)
* Handle `data={"key": [None|int|float|bool]}` cases. (Pull #1539)
* Support `httpx.URL(**kwargs)`, for example `httpx.URL(scheme="https", host="www.example.com", path="/')`, or `httpx.URL("https://www.example.com/", username="tom@gmail.com", password="123 456")`. (Pull #1601)
* Support `url.copy_with(params=...)`. (Pull #1601)
* Add `url.params` parameter, returning an immutable `QueryParams` instance. (Pull #1601)
* Support query manipulation methods on the URL class. These are `url.copy_set_param()`, `url.copy_add_param()`, `url.copy_remove_param()`, `url.copy_merge_params()`. (Pull #1601)
* The `httpx.URL` class now performs port normalization, so `:80` ports are stripped from `http` URLs and `:443` ports are stripped from `https` URLs. (Pull #1603)
* The `URL.host` property returns unicode strings for internationalized domain names. The `URL.raw_host` property returns byte strings with IDNA escaping applied. (Pull #1590)

### Fixed

* Fix Content-Length for cases of `files=...` where unicode string is used as the file content. (Pull #1537)
* Fix some cases of merging relative URLs against `Client(base_url=...)`. (Pull #1532)
* The `request.content` attribute is now always available except for streaming content, which requires an explicit `.read()`. (Pull #1583)

## 0.17.1 (March 15th, 2021)

### Fixed

* Type annotation on `CertTypes` allows `keyfile` and `password` to be optional. (Pull #1503)
* Fix httpcore pinned version. (Pull #1495)

## 0.17.0 (February 28th, 2021)

### Added

* Add `httpx.MockTransport()`, allowing to mock out a transport using pre-determined responses. (Pull #1401, Pull #1449)
* Add `httpx.HTTPTransport()` and `httpx.AsyncHTTPTransport()` default transports. (Pull #1399)
* Add mount API support, using `httpx.Client(mounts=...)`. (Pull #1362)
* Add `chunk_size` parameter to `iter_raw()`, `iter_bytes()`, `iter_text()`. (Pull #1277)
* Add `keepalive_expiry` parameter to `httpx.Limits()` configuration. (Pull #1398)
* Add repr to `httpx.Cookies` to display available cookies. (Pull #1411)
* Add support for `params=<tuple>` (previously only `params=<list>` was supported). (Pull #1426)

### Fixed

* Add missing `raw_path` to ASGI scope. (Pull #1357)
* Tweak `create_ssl_context` defaults to use `trust_env=True`. (Pull #1447)
* Properly URL-escape WSGI `PATH_INFO`. (Pull #1391)
* Properly set default ports in WSGI transport. (Pull #1469)
* Properly encode slashes when using `base_url`. (Pull #1407)
* Properly map exceptions in `request.aclose()`. (Pull #1465)

## 0.16.1 (October 8th, 2020)

### Fixed

* Support literal IPv6 addresses in URLs. (Pull #1349)
* Force lowercase headers in ASGI scope dictionaries. (Pull #1351)

## 0.16.0 (October 6th, 2020)

### Changed

* Preserve HTTP header casing. (Pull #1338, encode/httpcore#216, python-hyper/h11#104)
* Drop `response.next()` and `response.anext()` methods in favour of `response.next_request` attribute. (Pull #1339)
* Closed clients now raise a runtime error if attempting to send a request. (Pull #1346)

### Added

* Add Python 3.9 to officially supported versions.
* Type annotate `__enter__`/`__exit__`/`__aenter__`/`__aexit__` in a way that supports subclasses of `Client` and `AsyncClient`. (Pull #1336)

## 0.15.5 (October 1st, 2020)

### Added

* Add `response.next_request` (Pull #1334)

## 0.15.4 (September 25th, 2020)

### Added

* Support direct comparisons between `Headers` and dicts or lists of two-tuples. Eg. `assert response.headers == {"Content-Length": 24}` (Pull #1326)

### Fixed

* Fix automatic `.read()` when `Response` instances are created with `content=<str>` (Pull #1324)

## 0.15.3 (September 24th, 2020)

### Fixed

* Fixed connection leak in async client due to improper closing of response streams. (Pull #1316)

## 0.15.2 (September 23nd, 2020)

### Fixed

* Fixed `response.elapsed` property. (Pull #1313)
* Fixed client authentication interaction with `.stream()`. (Pull #1312)

## 0.15.1 (September 23nd, 2020)

### Fixed

* ASGITransport now properly applies URL decoding to the `path` component, as-per the ASGI spec. (Pull #1307)

## 0.15.0 (September 22nd, 2020)

### Added

* Added support for curio. (Pull https://github.com/encode/httpcore/pull/168)
* Added support for event hooks. (Pull #1246)
* Added support for authentication flows which require either sync or async I/O. (Pull #1217)
* Added support for monitoring download progress with `response.num_bytes_downloaded`. (Pull #1268)
* Added `Request(content=...)` for byte content, instead of overloading `Request(data=...)` (Pull #1266)
* Added support for all URL components as parameter names when using `url.copy_with(...)`. (Pull #1285)
* Neater split between automatically populated headers on `Request` instances, vs default `client.headers`. (Pull #1248)
* Unclosed `AsyncClient` instances will now raise warnings if garbage collected. (Pull #1197)
* Support `Response(content=..., text=..., html=..., json=...)` for creating usable response instances in code. (Pull #1265, #1297)
* Support instantiating requests from the low-level transport API. (Pull #1293)
* Raise errors on invalid URL types. (Pull #1259)

### Changed

* Cleaned up expected behaviour for URL escaping. `url.path` is now URL escaped. (Pull #1285)
* Cleaned up expected behaviour for bytes vs str in URL components. `url.userinfo` and `url.query` are not URL escaped, and so return bytes. (Pull #1285)
* Drop `url.authority` property in favour of `url.netloc`, since "authority" was semantically incorrect. (Pull #1285)
* Drop `url.full_path` property in favour of `url.raw_path`, for better consistency with other parts of the API. (Pull #1285)
* No longer use the `chardet` library for auto-detecting charsets, instead defaulting to a simpler approach when no charset is specified. (#1269)

### Fixed

* Swapped ordering of redirects and authentication flow. (Pull #1267)
* `.netrc` lookups should use host, not host+port. (Pull #1298)

### Removed

* The `URLLib3Transport` class no longer exists. We've published it instead as an example of [a custom transport class](https://gist.github.com/florimondmanca/d56764d78d748eb9f73165da388e546e). (Pull #1182)
* Drop `request.timer` attribute, which was being used internally to set `response.elapsed`. (Pull #1249)
* Drop `response.decoder` attribute, which was being used internally. (Pull #1276)
* `Request.prepare()` is now a private method. (Pull #1284)
* The `Headers.getlist()` method had previously been deprecated in favour of `Headers.get_list()`. It is now fully removed.
* The `QueryParams.getlist()` method had previously been deprecated in favour of `QueryParams.get_list()`. It is now fully removed.
* The `URL.is_ssl` property had previously been deprecated in favour of `URL.scheme == "https"`. It is now fully removed.
* The `httpx.PoolLimits` class had previously been deprecated in favour of `httpx.Limits`. It is now fully removed.
* The `max_keepalive` setting had previously been deprecated in favour of the more explicit `max_keepalive_connections`. It is now fully removed.
* The verbose `httpx.Timeout(5.0, connect_timeout=60.0)` style had previously been deprecated in favour of `httpx.Timeout(5.0, connect=60.0)`. It is now fully removed.
* Support for instantiating a timeout config missing some defaults, such as `httpx.Timeout(connect=60.0)`, had previously been deprecated in favour of enforcing a more explicit style, such as `httpx.Timeout(5.0, connect=60.0)`. This is now strictly enforced.

## 0.14.3 (September 2nd, 2020)

### Added

* `http.Response()` may now be instantiated without a `request=...` parameter. Useful for some unit testing cases. (Pull #1238)
* Add `103 Early Hints` and `425 Too Early` status codes. (Pull #1244)

### Fixed

* `DigestAuth` now handles responses that include multiple 'WWW-Authenticate' headers. (Pull #1240)
* Call into transport `__enter__`/`__exit__` or `__aenter__`/`__aexit__` when client is used in a context manager style. (Pull #1218)

## 0.14.2 (August 24th, 2020)

### Added

* Support `client.get(..., auth=None)` to bypass the default authentication on a clients. (Pull #1115)
* Support `client.auth = ...` property setter. (Pull #1185)
* Support `httpx.get(..., proxies=...)` on top-level request functions. (Pull #1198)
* Display instances with nicer import styles. (Eg. <httpx.ReadTimeout ...>) (Pull #1155)
* Support `cookies=[(key, value)]` list-of-two-tuples style usage. (Pull #1211)

### Fixed

* Ensure that automatically included headers on a request may be modified. (Pull #1205)
* Allow explicit `Content-Length` header on streaming requests. (Pull #1170)
* Handle URL quoted usernames and passwords properly. (Pull #1159)
* Use more consistent default for `HEAD` requests, setting `allow_redirects=True`. (Pull #1183)
* If a transport error occurs while streaming the response, raise an `httpx` exception, not the underlying `httpcore` exception. (Pull #1190)
* Include the underlying `httpcore` traceback, when transport exceptions occur. (Pull #1199)

## 0.14.1 (August 11th, 2020)

### Added

* The `httpx.URL(...)` class now raises `httpx.InvalidURL` on invalid URLs, rather than exposing the underlying `rfc3986` exception. If a redirect response includes an invalid 'Location' header, then a `RemoteProtocolError` exception is raised, which will be associated with the request that caused it. (Pull #1163)

### Fixed

* Handling multiple `Set-Cookie` headers became broken in the 0.14.0 release, and is now resolved. (Pull #1156)

## 0.14.0 (August 7th, 2020)

The 0.14 release includes a range of improvements to the public API, intended on preparing for our upcoming 1.0 release.

* Our HTTP/2 support is now fully optional. **You now need to use `pip install httpx[http2]` if you want to include the HTTP/2 dependencies.**
* Our HSTS support has now been removed. Rewriting URLs from `http` to `https` if the host is on the HSTS list can be beneficial in avoiding roundtrips to incorrectly formed URLs, but on balance we've decided to remove this feature, on the principle of least surprise. Most programmatic clients do not include HSTS support, and for now we're opting to remove our support for it.
* Our exception hierarchy has been overhauled. Most users will want to stick with their existing `httpx.HTTPError` usage, but we've got a clearer overall structure now. See https://www.python-httpx.org/exceptions/ for more details.

When upgrading you should be aware of the following public API changes. Note that deprecated usages will currently continue to function, but will issue warnings.

* You should now use `httpx.codes` consistently instead of `httpx.StatusCodes`.
* Usage of `httpx.Timeout()` should now always include an explicit default. Eg. `httpx.Timeout(None, pool=5.0)`.
* When using `httpx.Timeout()`, we now have more concisely named keyword arguments. Eg. `read=5.0`, instead of `read_timeout=5.0`.
* Use `httpx.Limits()` instead of `httpx.PoolLimits()`, and `limits=...` instead of `pool_limits=...`.
* The `httpx.Limits(max_keepalive=...)` argument is now deprecated in favour of a more explicit `httpx.Limits(max_keepalive_connections=...)`.
* Keys used with `Client(proxies={...})` should now be in the style of `{"http://": ...}`, rather than `{"http": ...}`.
* The multidict methods `Headers.getlist()` and `QueryParams.getlist()` are deprecated in favour of more consistent `.get_list()` variants.
* The `URL.is_ssl` property is deprecated in favour of `URL.scheme == "https"`.
* The `URL.join(relative_url=...)` method is now `URL.join(url=...)`. This change does not support warnings for the deprecated usage style.

One notable aspect of the 0.14.0 release is that it tightens up the public API for `httpx`, by ensuring that several internal attributes and methods have now become strictly private.

The following previously had nominally public names on the client, but were all undocumented and intended solely for internal usage. They are all now replaced with underscored names, and should not be relied on or accessed.

These changes should not affect users who have been working from the `httpx` documentation.

* `.merge_url()`, `.merge_headers()`, `.merge_cookies()`, `.merge_queryparams()`
* `.build_auth()`, `.build_redirect_request()`
* `.redirect_method()`, `.redirect_url()`, `.redirect_headers()`, `.redirect_stream()`
* `.send_handling_redirects()`, `.send_handling_auth()`, `.send_single_request()`
* `.init_transport()`, `.init_proxy_transport()`
* `.proxies`, `.transport`, `.netrc`, `.get_proxy_map()`

See pull requests #997, #1065, #1071.

Some areas of API which were already on the deprecation path, and were raising warnings or errors in 0.13.x have now been escalated to being fully removed.

* Drop `ASGIDispatch`, `WSGIDispatch`, which have been replaced by `ASGITransport`, `WSGITransport`.
* Drop `dispatch=...`` on client, which has been replaced by `transport=...``
* Drop `soft_limit`, `hard_limit`, which have been replaced by `max_keepalive` and `max_connections`.
* Drop `Response.stream` and` `Response.raw`, which have been replaced by ``.aiter_bytes` and `.aiter_raw`.
* Drop `proxies=<transport instance>` in favor of `proxies=httpx.Proxy(...)`.

See pull requests #1057, #1058.

### Added

* Added dedicated exception class `httpx.HTTPStatusError` for `.raise_for_status()` exceptions. (Pull #1072)
* Added `httpx.create_ssl_context()` helper function. (Pull #996)
* Support for proxy exclusions like `proxies={"https://www.example.com": None}`. (Pull #1099)
* Support `QueryParams(None)` and `client.params = None`. (Pull #1060)

### Changed

* Use `httpx.codes` consistently in favour of `httpx.StatusCodes` which is placed into deprecation. (Pull #1088)
* Usage of `httpx.Timeout()` should now always include an explicit default. Eg. `httpx.Timeout(None, pool=5.0)`. (Pull #1085)
* Switch to more concise `httpx.Timeout()` keyword arguments. Eg. `read=5.0`, instead of `read_timeout=5.0`. (Pull #1111)
* Use `httpx.Limits()` instead of `httpx.PoolLimits()`, and `limits=...` instead of `pool_limits=...`. (Pull #1113)
* Keys used with `Client(proxies={...})` should now be in the style of `{"http://": ...}`, rather than `{"http": ...}`. (Pull #1127)
* The multidict methods `Headers.getlist` and `QueryParams.getlist` are deprecated in favour of more consistent `.get_list()` variants. (Pull #1089)
* `URL.port` becomes `Optional[int]`. Now only returns a port if one is explicitly included in the URL string. (Pull #1080)
* The `URL(..., allow_relative=[bool])` parameter no longer exists. All URL instances may be relative. (Pull #1073)
* Drop unnecessary `url.full_path = ...` property setter. (Pull #1069)
* The `URL.join(relative_url=...)` method is now `URL.join(url=...)`. (Pull #1129)
* The `URL.is_ssl` property is deprecated in favour of `URL.scheme == "https"`. (Pull #1128)

### Fixed

* Add missing `Response.next()` method. (Pull #1055)
* Ensure all exception classes are exposed as public API. (Pull #1045)
* Support multiple items with an identical field name in multipart encodings. (Pull #777)
* Skip HSTS preloading on single-label domains. (Pull #1074)
* Fixes for `Response.iter_lines()`. (Pull #1033, #1075)
* Ignore permission errors when accessing `.netrc` files. (Pull #1104)
* Allow bare hostnames in `HTTP_PROXY` etc... environment variables. (Pull #1120)
* Settings `app=...` or `transport=...` bypasses any environment based proxy defaults. (Pull #1122)
* Fix handling of `.base_url` when a path component is included in the base URL. (Pull #1130)

---

## 0.13.3 (May 29th, 2020)

### Fixed

* Include missing keepalive expiry configuration. (Pull #1005)
* Improved error message when URL redirect has a custom scheme. (Pull #1002)

## 0.13.2 (May 27th, 2020)

### Fixed

* Include explicit "Content-Length: 0" on POST, PUT, PATCH if no request body is used. (Pull #995)
* Add `http2` option to `httpx.Client`. (Pull #982)
* Tighten up API typing in places. (Pull #992, #999)

## 0.13.1 (May 22nd, 2020)

### Fixed

* Fix pool options deprecation warning. (Pull #980)
* Include `httpx.URLLib3ProxyTransport` in top-level API. (Pull #979)

## 0.13.0 (May 22nd, 2020)

This release switches to `httpcore` for all the internal networking, which means:

* We're using the same codebase for both our sync and async clients.
* HTTP/2 support is now available with the sync client.
* We no longer have a `urllib3` dependency for our sync client, although there is still an *optional* `URLLib3Transport` class.

It also means we've had to remove our UDS support, since maintaining that would have meant having to push back our work towards a 1.0 release, which isn't a trade-off we wanted to make.

We also now have [a public "Transport API"](https://www.python-httpx.org/advanced/transports/#custom-transports), which you can use to implement custom transport implementations against. This formalises and replaces our previously private "Dispatch API".

### Changed

* Use `httpcore` for underlying HTTP transport. Drop `urllib3` requirement. (Pull #804, #967)
* Rename pool limit options from `soft_limit`/`hard_limit` to `max_keepalive`/`max_connections`. (Pull #968)
* The previous private "Dispatch API" has now been promoted to a public "Transport API". When customizing the transport use `transport=...`. The `ASGIDispatch` and `WSGIDispatch` class naming is deprecated in favour of `ASGITransport` and `WSGITransport`. (Pull #963)

### Added

* Added `URLLib3Transport` class for optional `urllib3` transport support. (Pull #804, #963)
* Streaming multipart uploads. (Pull #857)
* Logging via HTTPCORE_LOG_LEVEL and HTTPX_LOG_LEVEL environment variables
and TRACE level logging. (Pull encode/httpcore#79)

### Fixed

* Performance improvement in brotli decoder. (Pull #906)
* Proper warning level of deprecation notice in `Response.stream` and `Response.raw`. (Pull #908)
* Fix support for generator based WSGI apps. (Pull #887)
* Reuse of connections on HTTP/2 in close concurrency situations. (Pull encode/httpcore#81)
* Honor HTTP/2 max concurrent streams settings (Pull encode/httpcore#89, encode/httpcore#90)
* Fix bytes support in multipart uploads. (Pull #974)
* Improve typing support for `files=...`. (Pull #976)

### Removed

* Dropped support for `Client(uds=...)` (Pull #804)

## 0.13.0.dev2 (May 12th, 2020)

The 0.13.0.dev2 is a *pre-release* version. To install it, use `pip install httpx --pre`.

### Added

* Logging via HTTPCORE_LOG_LEVEL and HTTPX_LOG_LEVEL environment variables
and TRACE level logging. (HTTPCore Pull #79)

### Fixed

* Reuse of connections on HTTP/2 in close concurrency situations. (HTTPCore Pull #81)
* When using an `app=<ASGI app>` observe neater disconnect behaviour instead of sending empty body messages. (Pull #919)

## 0.13.0.dev1 (May 6th, 2020)

The 0.13.0.dev1 is a *pre-release* version. To install it, use `pip install httpx --pre`.

### Fixed

* Passing `http2` flag to proxy dispatchers. (Pull #934)
* Use [`httpcore` v0.8.3](https://github.com/encode/httpcore/releases/tag/0.8.3)
which addresses problems in handling of headers when using proxies.

## 0.13.0.dev0 (April 30th, 2020)

The 0.13.0.dev0 is a *pre-release* version. To install it, use `pip install httpx --pre`.

This release switches to `httpcore` for all the internal networking, which means:

* We're using the same codebase for both our sync and async clients.
* HTTP/2 support is now available with the sync client.
* We no longer have a `urllib3` dependency for our sync client, although there is still an *optional* `URLLib3Dispatcher` class.

It also means we've had to remove our UDS support, since maintaining that would have meant having to push back our work towards a 1.0 release, which isn't a trade-off we wanted to make.

### Changed

* Use `httpcore` for underlying HTTP transport. Drop `urllib3` requirement. (Pull #804)

### Added

* Added `URLLib3Dispatcher` class for optional `urllib3` transport support. (Pull #804)
* Streaming multipart uploads. (Pull #857)

### Fixed

* Performance improvement in brotli decoder. (Pull #906)
* Proper warning level of deprecation notice in `Response.stream` and `Response.raw`. (Pull #908)
* Fix support for generator based WSGI apps. (Pull #887)

### Removed

* Dropped support for `Client(uds=...)` (Pull #804)

---

## 0.12.1 (March 19th, 2020)

### Fixed

* Resolved packaging issue, where additional files were being included.

## 0.12.0 (March 9th, 2020)

The 0.12 release tightens up the API expectations for `httpx` by switching to private module names to enforce better clarity around public API.

All imports of `httpx` should import from the top-level package only, such as `from httpx import Request`, rather than importing from privately namespaced modules such as `from httpx._models import Request`.

### Added

* Support making response body available to auth classes with `.requires_response_body`. (Pull #803)
* Export `NetworkError` exception. (Pull #814)
* Add support for `NO_PROXY` environment variable. (Pull #835)

### Changed

* Switched to private module names. (Pull #785)
* Drop redirect looping detection and the `RedirectLoop` exception, instead using `TooManyRedirects`. (Pull #819)
* Drop `backend=...` parameter on `AsyncClient`, in favour of always autodetecting `trio`/`asyncio`. (Pull #791)

### Fixed

* Support basic auth credentials in proxy URLs. (Pull #780)
* Fix `httpx.Proxy(url, mode="FORWARD_ONLY")` configuration. (Pull #788)
* Fallback to setting headers as UTF-8 if no encoding is specified. (Pull #820)
* Close proxy dispatches classes on client close. (Pull #826)
* Support custom `cert` parameters even if `verify=False`. (Pull #796)
* Don't support invalid dict-of-dicts form data in `data=...`. (Pull #811)

---

## 0.11.1 (January 17th, 2020)

### Fixed

* Fixed usage of `proxies=...` on `Client()`. (Pull #763)
* Support both `zlib` and `deflate` style encodings on `Content-Encoding: deflate`. (Pull #758)
* Fix for streaming a redirect response body with `allow_redirects=False`. (Pull #766)
* Handle redirect with malformed Location headers missing host. (Pull #774)

## 0.11.0 (January 9th, 2020)

The 0.11 release reintroduces our sync support, so that `httpx` now supports both a standard thread-concurrency API, and an async API.

Existing async `httpx` users that are upgrading to 0.11 should ensure that:

* Async codebases should always use a client instance to make requests, instead of the top-level API.
* The async client is named as `httpx.AsyncClient()`, instead of `httpx.Client()`.
* When instantiating proxy configurations use the `httpx.Proxy()` class, instead of the previous `httpx.HTTPProxy()`. This new configuration class works for configuring both sync and async clients.

We believe the API is now pretty much stable, and are aiming for a 1.0 release sometime on or before April 2020.

### Changed

- Top level API such as `httpx.get(url, ...)`, `httpx.post(url, ...)`, `httpx.request(method, url, ...)` becomes synchronous.
- Added `httpx.Client()` for synchronous clients, with `httpx.AsyncClient` being used for async clients.
- Switched to `proxies=httpx.Proxy(...)` for proxy configuration.
- Network connection errors are wrapped in `httpx.NetworkError`, rather than exposing lower-level exception types directly.

### Removed

- The `request.url.origin` property and `httpx.Origin` class are no longer available.
- The per-request `cert`, `verify`, and `trust_env` arguments are escalated from raising errors if used, to no longer being available. These arguments should be used on a per-client instance instead, or in the top-level API.
- The `stream` argument has escalated from raising an error when used, to no longer being available. Use the `client.stream(...)` or `httpx.stream()` streaming API instead.

### Fixed

- Redirect loop detection matches against `(method, url)` rather than `url`. (Pull #734)

---

## 0.10.1 (December 31st, 2019)

### Fixed

- Fix issue with concurrent connection acquisition. (Pull #700)
- Fix write error on closing HTTP/2 connections. (Pull #699)

## 0.10.0 (December 29th, 2019)

The 0.10.0 release makes some changes that will allow us to support both sync and async interfaces.

In particular with streaming responses the `response.read()` method becomes `response.aread()`, and the `response.close()` method becomes `response.aclose()`.

If following redirects explicitly the `response.next()` method becomes `response.anext()`.

### Fixed

- End HTTP/2 streams immediately on no-body requests, rather than sending an empty body message. (Pull #682)
- Improve typing for `Response.request`: switch from `Optional[Request]` to `Request`. (Pull #666)
- `Response.elapsed` now reflects the entire download time. (Pull #687, #692)

### Changed

- Added `AsyncClient` as a synonym for `Client`. (Pull #680)
- Switch to `response.aread()` for conditionally reading streaming responses. (Pull #674)
- Switch to `response.aclose()` and `client.aclose()` for explicit closing. (Pull #674, #675)
- Switch to `response.anext()` for resolving the next redirect response. (Pull #676)

### Removed

- When using a client instance, the per-request usage of `verify`, `cert`, and `trust_env` have now escalated from raising a warning to raising an error. You should set these arguments on the client instead. (Pull #617)
- Removed the undocumented `request.read()`, since end users should not require it.

---

## 0.9.5 (December 20th, 2019)

### Fixed

- Fix Host header and HSTS rewrites when an explicit `:80` port is included in URL. (Pull #649)
- Query Params on the URL string are merged with any `params=...` argument. (Pull #653)
- More robust behavior when closing connections. (Pull #640)
- More robust behavior when handling HTTP/2 headers with trailing whitespace. (Pull #637)
- Allow any explicit `Content-Type` header to take precedence over the encoding default. (Pull #633)

## 0.9.4 (December 12th, 2019)

### Fixed

- Added expiry to Keep-Alive connections, resolving issues with acquiring connections. (Pull #627)
- Increased flow control windows on HTTP/2, resolving download speed issues. (Pull #629)

## 0.9.3 (December 7th, 2019)

### Fixed

- Fixed HTTP/2 with autodetection backend. (Pull #614)

## 0.9.2 (December 7th, 2019)

* Released due to packaging build artifact.

## 0.9.1 (December 6th, 2019)

* Released due to packaging build artifact.

## 0.9.0 (December 6th, 2019)

The 0.9 releases brings some major new features, including:

* A new streaming API.
* Autodetection of either asyncio or trio.
* Nicer timeout configuration.
* HTTP/2 support off by default, but can be enabled.

We've also removed all private types from the top-level package export.

In order to ensure you are only ever working with public API you should make
sure to only import the top-level package eg. `import httpx`, rather than
importing modules within the package.

### Added

- Added concurrency backend autodetection. (Pull #585)
- Added `Client(backend='trio')` and `Client(backend='asyncio')` API. (Pull #585)
- Added `response.stream_lines()` API. (Pull #575)
- Added `response.is_error` API. (Pull #574)
- Added support for `timeout=Timeout(5.0, connect_timeout=60.0)` styles. (Pull #593)

### Fixed

- Requests or Clients with `timeout=None` now correctly always disable timeouts. (Pull #592)
- Request 'Authorization' headers now have priority over `.netrc` authentication info. (Commit 095b691)
- Files without a filename no longer set a Content-Type in multipart data. (Commit ed94950)

### Changed

- Added `httpx.stream()` API. Using `stream=True` now results in a warning. (Pull #600, #610)
- HTTP/2 support is switched to "off by default", but can be enabled explicitly. (Pull #584)
- Switched to `Client(http2=True)` API from `Client(http_versions=["HTTP/1.1", "HTTP/2"])`. (Pull #586)
- Removed all private types from the top-level package export. (Pull #608)
- The SSL configuration settings of `verify`, `cert`, and `trust_env` now raise warnings if used per-request when using a Client instance. They should always be set on the Client instance itself. (Pull #597)
- Use plain strings "TUNNEL_ONLY" or "FORWARD_ONLY" on the HTTPProxy `proxy_mode` argument. The `HTTPProxyMode` enum still exists, but its usage will raise warnings. (#610)
- Pool timeouts are now on the timeout configuration, not the pool limits configuration. (Pull #563)
- The timeout configuration is now named `httpx.Timeout(...)`, not `httpx.TimeoutConfig(...)`. The old version currently remains as a synonym for backwards compatibility.  (Pull #591)

---

## 0.8.0 (November 27, 2019)

### Removed

- The synchronous API has been removed, in order to allow us to fundamentally change how we approach supporting both sync and async variants. (See #588 for more details.)

---

## 0.7.8 (November 17, 2019)

### Added

- Add support for proxy tunnels for Python 3.6 + asyncio. (Pull #521)

## 0.7.7 (November 15, 2019)

### Fixed

- Resolve an issue with cookies behavior on redirect requests. (Pull #529)

### Added

- Add request/response DEBUG logs. (Pull #502)
- Use TRACE log level for low level info. (Pull #500)

## 0.7.6 (November 2, 2019)

### Removed

- Drop `proxies` parameter from the high-level API. (Pull #485)

### Fixed

- Tweak multipart files: omit null filenames, add support for `str` file contents. (Pull #482)
- Cache NETRC authentication per-client. (Pull #400)
- Rely on `getproxies` for all proxy environment variables. (Pull #470)
- Wait for the `asyncio` stream to close when closing a connection. (Pull #494)

## 0.7.5 (October 10, 2019)

### Added

- Allow lists of values to be passed to `params`. (Pull #386)
- `ASGIDispatch`, `WSGIDispatch` are now available in the `httpx.dispatch` namespace. (Pull #407)
- `HTTPError` is now available in the `httpx` namespace.  (Pull #421)
- Add support for `start_tls()` to the Trio concurrency backend. (Pull #467)

### Fixed

- Username and password are no longer included in the `Host` header when basic authentication
  credentials are supplied via the URL. (Pull #417)

### Removed

- The `.delete()` function no longer has `json`, `data`, or `files` parameters
  to match the expected semantics of the `DELETE` method. (Pull #408)
- Removed the `trio` extra. Trio support is detected automatically. (Pull #390)

## 0.7.4 (September 25, 2019)

### Added

- Add Trio concurrency backend. (Pull #276)
- Add `params` parameter to `Client` for setting default query parameters. (Pull #372)
- Add support for `SSL_CERT_FILE` and `SSL_CERT_DIR` environment variables. (Pull #307)
- Add debug logging to calls into ASGI apps. (Pull #371)
- Add debug logging to SSL configuration. (Pull #378)

### Fixed

- Fix a bug when using `Client` without timeouts in Python 3.6. (Pull #383)
- Propagate `Client` configuration to HTTP proxies. (Pull #377)

## 0.7.3 (September 20, 2019)

### Added

- HTTP Proxy support. (Pulls #259, #353)
- Add Digest authentication. (Pull #332)
- Add `.build_request()` method to `Client` and `AsyncClient`. (Pull #319)
- Add `.elapsed` property on responses. (Pull #351)
- Add support for `SSLKEYLOGFILE` in Python 3.8b4+. (Pull #301)

### Removed

- Drop NPN support for HTTP version negotiation. (Pull #314)

### Fixed

- Fix distribution of type annotations for mypy (Pull #361).
- Set `Host` header when redirecting cross-origin. (Pull #321)
- Drop `Content-Length` headers on `GET` redirects. (Pull #310)
- Raise `KeyError` if header isn't found in `Headers`. (Pull #324)
- Raise `NotRedirectResponse` in `response.next()` if there is no redirection to perform. (Pull #297)
- Fix bug in calculating the HTTP/2 maximum frame size. (Pull #153)

## 0.7.2 (August 28, 2019)

- Enforce using `httpx.AsyncioBackend` for the synchronous client. (Pull #232)
- `httpx.ConnectionPool` will properly release a dropped connection. (Pull #230)
- Remove the `raise_app_exceptions` argument from `Client`. (Pull #238)
- `DecodeError` will no longer be raised for an empty body encoded with Brotli. (Pull #237)
- Added `http_versions` parameter to `Client`. (Pull #250)
- Only use HTTP/1.1 on short-lived connections like `httpx.get()`. (Pull #284)
- Convert `Client.cookies` and `Client.headers` when set as a property. (Pull #274)
- Setting `HTTPX_DEBUG=1` enables debug logging on all requests. (Pull #277)

## 0.7.1 (August 18, 2019)

- Include files with source distribution to be installable. (Pull #233)

## 0.7.0 (August 17, 2019)

- Add the `trust_env` property to `BaseClient`. (Pull #187)
- Add the `links` property to `BaseResponse`. (Pull #211)
- Accept `ssl.SSLContext` instances into `SSLConfig(verify=...)`. (Pull #215)
- Add `Response.stream_text()` with incremental encoding detection. (Pull #183)
- Properly updated the `Host` header when a redirect changes the origin. (Pull #199)
- Ignore invalid `Content-Encoding` headers. (Pull #196)
- Use `~/.netrc` and `~/_netrc` files by default when `trust_env=True`. (Pull #189)
- Create exception base class `HTTPError` with `request` and `response` properties. (Pull #162)
- Add HSTS preload list checking within `BaseClient` to upgrade HTTP URLs to HTTPS. (Pull #184)
- Switch IDNA encoding from IDNA 2003 to IDNA 2008. (Pull #161)
- Expose base classes for alternate concurrency backends. (Pull #178)
- Improve Multipart parameter encoding. (Pull #167)
- Add the `headers` property to `BaseClient`. (Pull #159)
- Add support for Google's `brotli` library. (Pull #156)
- Remove deprecated TLS versions (TLSv1 and TLSv1.1) from default `SSLConfig`. (Pull #155)
- Fix `URL.join(...)` to work similarly to RFC 3986 URL joining. (Pull #144)

---

## 0.6.8 (July 25, 2019)

- Check for disconnections when searching for an available
  connection in `ConnectionPool.keepalive_connections` (Pull #145)
- Allow string comparison for `URL` objects (Pull #139)
- Add HTTP status codes 418 and 451 (Pull #135)
- Add support for client certificate passwords (Pull #118)
- Enable post-handshake client cert authentication for TLSv1.3 (Pull #118)
- Disable using `commonName` for hostname checking for OpenSSL 1.1.0+ (Pull #118)
- Detect encoding for `Response.json()` (Pull #116)

## 0.6.7 (July 8, 2019)

- Check for connection aliveness on re-acquisition (Pull #111)

## 0.6.6 (July 3, 2019)

- Improve `USER_AGENT` (Pull #110)
- Add `Connection: keep-alive` by default to HTTP/1.1 connections. (Pull #110)

## 0.6.5 (June 27, 2019)

- Include `Host` header by default. (Pull #109)
- Improve HTTP protocol detection. (Pull #107)

## 0.6.4 (June 25, 2019)

- Implement read and write timeouts (Pull #104)

## 0.6.3 (June 24, 2019)

- Handle early connection closes (Pull #103)

## 0.6.2 (June 23, 2019)

- Use urllib3's `DEFAULT_CIPHERS` for the `SSLConfig` object. (Pull #100)

## 0.6.1 (June 21, 2019)

- Add support for setting a `base_url` on the `Client`.

## 0.6.0 (June 21, 2019)

- Honor `local_flow_control_window` for HTTP/2 connections (Pull #98)
