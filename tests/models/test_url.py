import pytest

import httpx

# Tests for `httpx.URL` instantiation and property accessors.


def test_basic_url():
    url = httpx.URL("https://www.example.com/")

    assert url.scheme == "https"
    assert url.userinfo == b""
    assert url.netloc == b"www.example.com"
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query == b""
    assert url.fragment == ""

    assert str(url) == "https://www.example.com/"
    assert repr(url) == "URL('https://www.example.com/')"


def test_complete_url():
    url = httpx.URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url.scheme == "https"
    assert url.host == "example.org"
    assert url.port == 123
    assert url.path == "/path/to/somewhere"
    assert url.query == b"abc=123"
    assert url.raw_path == b"/path/to/somewhere?abc=123"
    assert url.fragment == "anchor"

    assert str(url) == "https://example.org:123/path/to/somewhere?abc=123#anchor"
    assert (
        repr(url) == "URL('https://example.org:123/path/to/somewhere?abc=123#anchor')"
    )


def test_url_with_empty_query():
    """
    URLs with and without a trailing `?` but an empty query component
    should preserve the information on the raw path.
    """
    url = httpx.URL("https://www.example.com/path")
    assert url.path == "/path"
    assert url.query == b""
    assert url.raw_path == b"/path"

    url = httpx.URL("https://www.example.com/path?")
    assert url.path == "/path"
    assert url.query == b""
    assert url.raw_path == b"/path?"


def test_url_no_scheme():
    url = httpx.URL("://example.com")
    assert url.scheme == ""
    assert url.host == "example.com"
    assert url.path == "/"


def test_url_no_authority():
    url = httpx.URL("http://")
    assert url.scheme == "http"
    assert url.host == ""
    assert url.path == "/"


# Tests for percent encoding across path, query, and fragment...


@pytest.mark.parametrize(
    "url,raw_path,path,query,fragment",
    [
        # URL with unescaped chars in path.
        (
            "https://example.com/!$&'()*+,;= abc ABC 123 :/[]@",
            b"/!$&'()*+,;=%20abc%20ABC%20123%20:/[]@",
            "/!$&'()*+,;= abc ABC 123 :/[]@",
            b"",
            "",
        ),
        # URL with escaped chars in path.
        (
            "https://example.com/!$&'()*+,;=%20abc%20ABC%20123%20:/[]@",
            b"/!$&'()*+,;=%20abc%20ABC%20123%20:/[]@",
            "/!$&'()*+,;= abc ABC 123 :/[]@",
            b"",
            "",
        ),
        # URL with mix of unescaped and escaped chars in path.
        # WARNING: This has the incorrect behaviour, adding the test as an interim step.
        (
            "https://example.com/ %61%62%63",
            b"/%20%61%62%63",
            "/ abc",
            b"",
            "",
        ),
        # URL with unescaped chars in query.
        (
            "https://example.com/?!$&'()*+,;= abc ABC 123 :/[]@?",
            b"/?!$&'()*+,;=%20abc%20ABC%20123%20:/[]@?",
            "/",
            b"!$&'()*+,;=%20abc%20ABC%20123%20:/[]@?",
            "",
        ),
        # URL with escaped chars in query.
        (
            "https://example.com/?!$&%27()*+,;=%20abc%20ABC%20123%20:%2F[]@?",
            b"/?!$&%27()*+,;=%20abc%20ABC%20123%20:%2F[]@?",
            "/",
            b"!$&%27()*+,;=%20abc%20ABC%20123%20:%2F[]@?",
            "",
        ),
        # URL with mix of unescaped and escaped chars in query.
        (
            "https://example.com/?%20%97%98%99",
            b"/?%20%97%98%99",
            "/",
            b"%20%97%98%99",
            "",
        ),
        # URL encoding characters in fragment.
        (
            "https://example.com/#!$&'()*+,;= abc ABC 123 :/[]@?#",
            b"/",
            "/",
            b"",
            "!$&'()*+,;= abc ABC 123 :/[]@?#",
        ),
    ],
)
def test_path_query_fragment(url, raw_path, path, query, fragment):
    url = httpx.URL(url)
    assert url.raw_path == raw_path
    assert url.path == path
    assert url.query == query
    assert url.fragment == fragment


def test_url_query_encoding():
    url = httpx.URL("https://www.example.com/?a=b c&d=e/f")
    assert url.raw_path == b"/?a=b%20c&d=e/f"

    url = httpx.URL("https://www.example.com/?a=b+c&d=e/f")
    assert url.raw_path == b"/?a=b+c&d=e/f"

    url = httpx.URL("https://www.example.com/", params={"a": "b c", "d": "e/f"})
    assert url.raw_path == b"/?a=b+c&d=e%2Ff"


def test_url_params():
    url = httpx.URL("https://example.org:123/path/to/somewhere", params={"a": "123"})
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"
    assert url.params == httpx.QueryParams({"a": "123"})

    url = httpx.URL(
        "https://example.org:123/path/to/somewhere?b=456", params={"a": "123"}
    )
    assert str(url) == "https://example.org:123/path/to/somewhere?a=123"
    assert url.params == httpx.QueryParams({"a": "123"})


# Tests for username and password


@pytest.mark.parametrize(
    "url,userinfo,username,password",
    [
        # username and password in URL.
        (
            "https://username:password@example.com",
            b"username:password",
            "username",
            "password",
        ),
        # username and password in URL with percent escape sequences.
        (
            "https://username%40gmail.com:pa%20ssword@example.com",
            b"username%40gmail.com:pa%20ssword",
            "username@gmail.com",
            "pa ssword",
        ),
        (
            "https://user%20name:p%40ssword@example.com",
            b"user%20name:p%40ssword",
            "user name",
            "p@ssword",
        ),
        # username and password in URL without percent escape sequences.
        (
            "https://username@gmail.com:pa ssword@example.com",
            b"username%40gmail.com:pa%20ssword",
            "username@gmail.com",
            "pa ssword",
        ),
        (
            "https://user name:p@ssword@example.com",
            b"user%20name:p%40ssword",
            "user name",
            "p@ssword",
        ),
    ],
)
def test_url_username_and_password(url, userinfo, username, password):
    url = httpx.URL(url)
    assert url.userinfo == userinfo
    assert url.username == username
    assert url.password == password


# Tests for different host types


def test_url_valid_host():
    url = httpx.URL("https://example.com/")
    assert url.host == "example.com"


def test_url_normalized_host():
    url = httpx.URL("https://EXAMPLE.com/")
    assert url.host == "example.com"


def test_url_percent_escape_host():
    url = httpx.URL("https://exam le.com/")
    assert url.host == "exam%20le.com"


def test_url_ipv4_like_host():
    """rare host names used to quality as IPv4"""
    url = httpx.URL("https://023b76x43144/")
    assert url.host == "023b76x43144"


# Tests for different port types


def test_url_valid_port():
    url = httpx.URL("https://example.com:123/")
    assert url.port == 123


def test_url_normalized_port():
    # If the port matches the scheme default it is normalized to None.
    url = httpx.URL("https://example.com:443/")
    assert url.port is None


def test_url_invalid_port():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://example.com:abc/")
    assert str(exc.value) == "Invalid port: 'abc'"


# Tests for path handling


def test_url_normalized_path():
    url = httpx.URL("https://example.com/abc/def/../ghi/./jkl")
    assert url.path == "/abc/ghi/jkl"


def test_url_escaped_path():
    url = httpx.URL("https://example.com/ /🌟/")
    assert url.raw_path == b"/%20/%F0%9F%8C%9F/"


def test_url_leading_dot_prefix_on_absolute_url():
    url = httpx.URL("https://example.com/../abc")
    assert url.path == "/abc"


def test_url_leading_dot_prefix_on_relative_url():
    url = httpx.URL("../abc")
    assert url.path == "../abc"


# Tests for query parameter percent encoding.
#
# Percent-encoding in `params={}` should match browser form behavior.


def test_param_with_space():
    # Params passed as form key-value pairs should be form escaped,
    # Including the special case of "+" for space seperators.
    url = httpx.URL("http://webservice", params={"u": "with spaces"})
    assert str(url) == "http://webservice?u=with+spaces"


def test_param_requires_encoding():
    # Params passed as form key-value pairs should be escaped.
    url = httpx.URL("http://webservice", params={"u": "%"})
    assert str(url) == "http://webservice?u=%25"


def test_param_with_percent_encoded():
    # Params passed as form key-value pairs should always be escaped,
    # even if they include a valid escape sequence.
    # We want to match browser form behaviour here.
    url = httpx.URL("http://webservice", params={"u": "with%20spaces"})
    assert str(url) == "http://webservice?u=with%2520spaces"


def test_param_with_existing_escape_requires_encoding():
    # Params passed as form key-value pairs should always be escaped,
    # even if they include a valid escape sequence.
    # We want to match browser form behaviour here.
    url = httpx.URL("http://webservice", params={"u": "http://example.com?q=foo%2Fa"})
    assert str(url) == "http://webservice?u=http%3A%2F%2Fexample.com%3Fq%3Dfoo%252Fa"


# Tests for query parameter percent encoding.
#
# Percent-encoding in `url={}` should match browser URL bar behavior.


def test_query_with_existing_percent_encoding():
    # Valid percent encoded sequences should not be double encoded.
    url = httpx.URL("http://webservice?u=phrase%20with%20spaces")
    assert str(url) == "http://webservice?u=phrase%20with%20spaces"


def test_query_requiring_percent_encoding():
    # Characters that require percent encoding should be encoded.
    url = httpx.URL("http://webservice?u=phrase with spaces")
    assert str(url) == "http://webservice?u=phrase%20with%20spaces"


def test_query_with_mixed_percent_encoding():
    # When a mix of encoded and unencoded characters are present,
    # characters that require percent encoding should be encoded,
    # while existing sequences should not be double encoded.
    url = httpx.URL("http://webservice?u=phrase%20with spaces")
    assert str(url) == "http://webservice?u=phrase%20with%20spaces"


# Tests for invalid URLs


def test_url_invalid_hostname():
    """
    Ensure that invalid URLs raise an `httpx.InvalidURL` exception.
    """
    with pytest.raises(httpx.InvalidURL):
        httpx.URL("https://😇/")


def test_url_excessively_long_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com/" + "x" * 100_000)
    assert str(exc.value) == "URL too long"


def test_url_excessively_long_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com", path="/" + "x" * 100_000)
    assert str(exc.value) == "URL component 'path' too long"


def test_url_non_printing_character_in_url():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com/\n")
    assert str(exc.value) == (
        "Invalid non-printable ASCII character in URL, '\\n' at position 24."
    )


def test_url_non_printing_character_in_component():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://www.example.com", path="/\n")
    assert str(exc.value) == (
        "Invalid non-printable ASCII character in URL path component, "
        "'\\n' at position 1."
    )


# Test for url components


def test_url_with_components():
    url = httpx.URL(scheme="https", host="www.example.com", path="/")

    assert url.scheme == "https"
    assert url.userinfo == b""
    assert url.host == "www.example.com"
    assert url.port is None
    assert url.path == "/"
    assert url.query == b""
    assert url.fragment == ""

    assert str(url) == "https://www.example.com/"


def test_urlparse_with_invalid_component():
    with pytest.raises(TypeError) as exc:
        httpx.URL(scheme="https", host="www.example.com", incorrect="/")
    assert str(exc.value) == "'incorrect' is an invalid keyword argument for URL()"


def test_urlparse_with_invalid_scheme():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(scheme="~", host="www.example.com", path="/")
    assert str(exc.value) == "Invalid URL component 'scheme'"


def test_urlparse_with_invalid_path():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(scheme="https", host="www.example.com", path="abc")
    assert str(exc.value) == "For absolute URLs, path must be empty or begin with '/'"

    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(path="//abc")
    assert str(exc.value) == "Relative URLs cannot have a path starting with '//'"

    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL(path=":abc")
    assert str(exc.value) == "Relative URLs cannot have a path starting with ':'"


def test_url_with_relative_path():
    # This path would be invalid for an absolute URL, but is valid as a relative URL.
    url = httpx.URL(path="abc")
    assert url.path == "abc"


# Tests for `httpx.URL` python built-in operators.


def test_url_eq_str():
    """
    Ensure that `httpx.URL` supports the equality operator.
    """
    url = httpx.URL("https://example.org:123/path/to/somewhere?abc=123#anchor")
    assert url == "https://example.org:123/path/to/somewhere?abc=123#anchor"
    assert str(url) == url


def test_url_set():
    """
    Ensure that `httpx.URL` instances can be used in sets.
    """
    urls = (
        httpx.URL("http://example.org:123/path/to/somewhere"),
        httpx.URL("http://example.org:123/path/to/somewhere/else"),
    )

    url_set = set(urls)

    assert all(url in urls for url in url_set)


def test_custom_object_url():
    class ExternalURLClass:
        def __str__(self):
            return "https://www.example.com/"

    url = ExternalURLClass()
    httpx_url = httpx.URL(url)
    assert httpx_url == "https://www.example.com/"


# Tests for TypeErrors when instantiating `httpx.URL`.


def test_url_with_invalid_component():
    with pytest.raises(TypeError) as exc:
        httpx.URL(scheme="https", host="www.example.com", incorrect="/")
    assert str(exc.value) == "'incorrect' is an invalid keyword argument for URL()"


# Tests for `URL.join()`.


def test_url_join():
    """
    Some basic URL joining tests.
    """
    url = httpx.URL("https://example.org:123/path/to/somewhere")
    assert url.join("/somewhere-else") == "https://example.org:123/somewhere-else"
    assert (
        url.join("somewhere-else") == "https://example.org:123/path/to/somewhere-else"
    )
    assert (
        url.join("../somewhere-else") == "https://example.org:123/path/somewhere-else"
    )
    assert url.join("../../somewhere-else") == "https://example.org:123/somewhere-else"


def test_relative_url_join():
    url = httpx.URL("/path/to/somewhere")
    assert url.join("/somewhere-else") == "/somewhere-else"
    assert url.join("somewhere-else") == "/path/to/somewhere-else"
    assert url.join("../somewhere-else") == "/path/somewhere-else"
    assert url.join("../../somewhere-else") == "/somewhere-else"


def test_url_join_rfc3986():
    """
    URL joining tests, as-per reference examples in RFC 3986.

    https://tools.ietf.org/html/rfc3986#section-5.4
    """

    url = httpx.URL("http://example.com/b/c/d;p?q")

    assert url.join("g") == "http://example.com/b/c/g"
    assert url.join("./g") == "http://example.com/b/c/g"
    assert url.join("g/") == "http://example.com/b/c/g/"
    assert url.join("/g") == "http://example.com/g"
    assert url.join("//g") == "http://g"
    assert url.join("?y") == "http://example.com/b/c/d;p?y"
    assert url.join("g?y") == "http://example.com/b/c/g?y"
    assert url.join("#s") == "http://example.com/b/c/d;p?q#s"
    assert url.join("g#s") == "http://example.com/b/c/g#s"
    assert url.join("g?y#s") == "http://example.com/b/c/g?y#s"
    assert url.join(";x") == "http://example.com/b/c/;x"
    assert url.join("g;x") == "http://example.com/b/c/g;x"
    assert url.join("g;x?y#s") == "http://example.com/b/c/g;x?y#s"
    assert url.join("") == "http://example.com/b/c/d;p?q"
    assert url.join(".") == "http://example.com/b/c/"
    assert url.join("./") == "http://example.com/b/c/"
    assert url.join("..") == "http://example.com/b/"
    assert url.join("../") == "http://example.com/b/"
    assert url.join("../g") == "http://example.com/b/g"
    assert url.join("../..") == "http://example.com/"
    assert url.join("../../") == "http://example.com/"
    assert url.join("../../g") == "http://example.com/g"

    assert url.join("../../../g") == "http://example.com/g"
    assert url.join("../../../../g") == "http://example.com/g"

    assert url.join("/./g") == "http://example.com/g"
    assert url.join("/../g") == "http://example.com/g"
    assert url.join("g.") == "http://example.com/b/c/g."
    assert url.join(".g") == "http://example.com/b/c/.g"
    assert url.join("g..") == "http://example.com/b/c/g.."
    assert url.join("..g") == "http://example.com/b/c/..g"

    assert url.join("./../g") == "http://example.com/b/g"
    assert url.join("./g/.") == "http://example.com/b/c/g/"
    assert url.join("g/./h") == "http://example.com/b/c/g/h"
    assert url.join("g/../h") == "http://example.com/b/c/h"
    assert url.join("g;x=1/./y") == "http://example.com/b/c/g;x=1/y"
    assert url.join("g;x=1/../y") == "http://example.com/b/c/y"

    assert url.join("g?y/./x") == "http://example.com/b/c/g?y/./x"
    assert url.join("g?y/../x") == "http://example.com/b/c/g?y/../x"
    assert url.join("g#s/./x") == "http://example.com/b/c/g#s/./x"
    assert url.join("g#s/../x") == "http://example.com/b/c/g#s/../x"


def test_resolution_error_1833():
    """
    See https://github.com/encode/httpx/issues/1833
    """
    url = httpx.URL("https://example.com/?[]")
    assert url.join("/") == "https://example.com/"


# Tests for `URL.copy_with()`.


def test_copy_with():
    url = httpx.URL("https://www.example.com/")
    assert str(url) == "https://www.example.com/"

    url = url.copy_with()
    assert str(url) == "https://www.example.com/"

    url = url.copy_with(scheme="http")
    assert str(url) == "http://www.example.com/"

    url = url.copy_with(netloc=b"example.com")
    assert str(url) == "http://example.com/"

    url = url.copy_with(path="/abc")
    assert str(url) == "http://example.com/abc"


def test_url_copywith_authority_subcomponents():
    copy_with_kwargs = {
        "username": "username",
        "password": "password",
        "port": 444,
        "host": "example.net",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://username:password@example.net:444"


def test_url_copywith_netloc():
    copy_with_kwargs = {
        "netloc": b"example.net:444",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://example.net:444"


def test_url_copywith_userinfo_subcomponents():
    copy_with_kwargs = {
        "username": "tom@example.org",
        "password": "abc123@ %",
    }
    url = httpx.URL("https://example.org")
    new = url.copy_with(**copy_with_kwargs)
    assert str(new) == "https://tom%40example.org:abc123%40%20%@example.org"
    assert new.username == "tom@example.org"
    assert new.password == "abc123@ %"
    assert new.userinfo == b"tom%40example.org:abc123%40%20%"


def test_url_copywith_invalid_component():
    url = httpx.URL("https://example.org")
    with pytest.raises(TypeError):
        url.copy_with(pathh="/incorrect-spelling")
    with pytest.raises(TypeError):
        url.copy_with(userinfo="should be bytes")


def test_url_copywith_urlencoded_path():
    url = httpx.URL("https://example.org")
    url = url.copy_with(path="/path to somewhere")
    assert url.path == "/path to somewhere"
    assert url.query == b""
    assert url.raw_path == b"/path%20to%20somewhere"


def test_url_copywith_query():
    url = httpx.URL("https://example.org")
    url = url.copy_with(query=b"a=123")
    assert url.path == "/"
    assert url.query == b"a=123"
    assert url.raw_path == b"/?a=123"


def test_url_copywith_raw_path():
    url = httpx.URL("https://example.org")
    url = url.copy_with(raw_path=b"/some/path")
    assert url.path == "/some/path"
    assert url.query == b""
    assert url.raw_path == b"/some/path"

    url = httpx.URL("https://example.org")
    url = url.copy_with(raw_path=b"/some/path?")
    assert url.path == "/some/path"
    assert url.query == b""
    assert url.raw_path == b"/some/path?"

    url = httpx.URL("https://example.org")
    url = url.copy_with(raw_path=b"/some/path?a=123")
    assert url.path == "/some/path"
    assert url.query == b"a=123"
    assert url.raw_path == b"/some/path?a=123"


def test_url_copywith_security():
    """
    Prevent unexpected changes on URL after calling copy_with (CVE-2021-41945)
    """
    with pytest.raises(httpx.InvalidURL):
        httpx.URL("https://u:p@[invalid!]//evilHost/path?t=w#tw")

    url = httpx.URL("https://example.com/path?t=w#tw")
    bad = "https://xxxx:xxxx@xxxxxxx/xxxxx/xxx?x=x#xxxxx"
    with pytest.raises(httpx.InvalidURL):
        url.copy_with(scheme=bad)


# Tests for copy-modifying-parameters methods.
#
# `URL.copy_set_param()`
# `URL.copy_add_param()`
# `URL.copy_remove_param()`
# `URL.copy_merge_params()`


def test_url_set_param_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_set_param("a", "456") == "https://example.org:123/?a=456"


def test_url_add_param_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_add_param("a", "456") == "https://example.org:123/?a=123&a=456"


def test_url_remove_param_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_remove_param("a") == "https://example.org:123/"


def test_url_merge_params_manipulation():
    """
    Some basic URL query parameter manipulation.
    """
    url = httpx.URL("https://example.org:123/?a=123")
    assert url.copy_merge_params({"b": "456"}) == "https://example.org:123/?a=123&b=456"


# Tests for IDNA hostname support.


@pytest.mark.parametrize(
    "given,idna,host,raw_host,scheme,port",
    [
        (
            "http://中国.icom.museum:80/",
            "http://xn--fiqs8s.icom.museum:80/",
            "中国.icom.museum",
            b"xn--fiqs8s.icom.museum",
            "http",
            None,
        ),
        (
            "http://Königsgäßchen.de",
            "http://xn--knigsgchen-b4a3dun.de",
            "königsgäßchen.de",
            b"xn--knigsgchen-b4a3dun.de",
            "http",
            None,
        ),
        (
            "https://faß.de",
            "https://xn--fa-hia.de",
            "faß.de",
            b"xn--fa-hia.de",
            "https",
            None,
        ),
        (
            "https://βόλος.com:443",
            "https://xn--nxasmm1c.com:443",
            "βόλος.com",
            b"xn--nxasmm1c.com",
            "https",
            None,
        ),
        (
            "http://ශ්‍රී.com:444",
            "http://xn--10cl1a0b660p.com:444",
            "ශ්‍රී.com",
            b"xn--10cl1a0b660p.com",
            "http",
            444,
        ),
        (
            "https://نامه‌ای.com:4433",
            "https://xn--mgba3gch31f060k.com:4433",
            "نامه‌ای.com",
            b"xn--mgba3gch31f060k.com",
            "https",
            4433,
        ),
    ],
    ids=[
        "http_with_port",
        "unicode_tr46_compat",
        "https_without_port",
        "https_with_port",
        "http_with_custom_port",
        "https_with_custom_port",
    ],
)
def test_idna_url(given, idna, host, raw_host, scheme, port):
    url = httpx.URL(given)
    assert url == httpx.URL(idna)
    assert url.host == host
    assert url.raw_host == raw_host
    assert url.scheme == scheme
    assert url.port == port


def test_url_unescaped_idna_host():
    url = httpx.URL("https://中国.icom.museum/")
    assert url.raw_host == b"xn--fiqs8s.icom.museum"


def test_url_escaped_idna_host():
    url = httpx.URL("https://xn--fiqs8s.icom.museum/")
    assert url.raw_host == b"xn--fiqs8s.icom.museum"


def test_url_invalid_idna_host():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://☃.com/")
    assert str(exc.value) == "Invalid IDNA hostname: '☃.com'"


# Tests for IPv4 hostname support.


def test_url_valid_ipv4():
    url = httpx.URL("https://1.2.3.4/")
    assert url.host == "1.2.3.4"


def test_url_invalid_ipv4():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://999.999.999.999/")
    assert str(exc.value) == "Invalid IPv4 address: '999.999.999.999'"


# Tests for IPv6 hostname support.


def test_ipv6_url():
    url = httpx.URL("http://[::ffff:192.168.0.1]:5678/")

    assert url.host == "::ffff:192.168.0.1"
    assert url.netloc == b"[::ffff:192.168.0.1]:5678"


def test_url_valid_ipv6():
    url = httpx.URL("https://[2001:db8::ff00:42:8329]/")
    assert url.host == "2001:db8::ff00:42:8329"


def test_url_invalid_ipv6():
    with pytest.raises(httpx.InvalidURL) as exc:
        httpx.URL("https://[2001]/")
    assert str(exc.value) == "Invalid IPv6 address: '[2001]'"


@pytest.mark.parametrize("host", ["[::ffff:192.168.0.1]", "::ffff:192.168.0.1"])
def test_ipv6_url_from_raw_url(host):
    url = httpx.URL(scheme="https", host=host, port=443, path="/")

    assert url.host == "::ffff:192.168.0.1"
    assert url.netloc == b"[::ffff:192.168.0.1]"
    assert str(url) == "https://[::ffff:192.168.0.1]/"


@pytest.mark.parametrize(
    "url_str",
    [
        "http://127.0.0.1:1234",
        "http://example.com:1234",
        "http://[::ffff:127.0.0.1]:1234",
    ],
)
@pytest.mark.parametrize("new_host", ["[::ffff:192.168.0.1]", "::ffff:192.168.0.1"])
def test_ipv6_url_copy_with_host(url_str, new_host):
    url = httpx.URL(url_str).copy_with(host=new_host)

    assert url.host == "::ffff:192.168.0.1"
    assert url.netloc == b"[::ffff:192.168.0.1]:1234"
    assert str(url) == "http://[::ffff:192.168.0.1]:1234"
