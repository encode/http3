# emscripten specific test fixtures


import random
import textwrap
from typing import Any, Generator, Type, TypeVar

import pytest

import httpx

_coverage_count = 0


def _get_coverage_filename(prefix: str) -> str:
    global _coverage_count
    _coverage_count += 1
    rand_part = "".join([random.choice("1234567890") for x in range(20)])
    return prefix + rand_part + f".{_coverage_count}"


@pytest.fixture()
def selenium_with_jspi_if_possible(
    request: pytest.FixtureRequest, runtime: str, has_jspi: bool
) -> Generator[Any, None, None]:
    if has_jspi:  # pragma: no cover
        fixture_name = "selenium_jspi"
    else:
        fixture_name = "selenium"
    selenium_obj = request.getfixturevalue(fixture_name)
    yield selenium_obj


T = TypeVar("T", bound=object)


def wrapRunner(wrapped: T, has_jspi: bool) -> T:
    BaseType: Type[T] = type(wrapped)

    # need to ignore type of BaseType because it is dynamic
    class CoverageRunner(BaseType):  # type:ignore
        COVERAGE_INIT_CODE = textwrap.dedent(
            """
            import pyodide_js as pjs
            await pjs.loadPackage("coverage")
            from importlib.metadata import distribution
            source_file = str(distribution('httpx').locate_file('httpx'))
            import coverage
            _coverage= coverage.Coverage(source=[source_file])
            _coverage.start()
            """
        )

        COVERAGE_TEARDOWN_CODE = textwrap.dedent(
            """            
            _coverage.stop()
            _coverage.save()
            _coverage_datafile = open(".coverage","rb")
            _coverage_outdata = _coverage_datafile.read()
            # avoid polluting main namespace too much
            import js as _coverage_js
            # convert to js Array (as default conversion is TypedArray which does
            # bad things in firefox)
            _coverage_js.Array.from_(_coverage_outdata) # last line is return value
            """
        )

        def __init__(self, base_runner: T, has_jspi: bool):
            self.has_jspi = has_jspi
            # copy attributes of base_runner
            for k, v in base_runner.__dict__.items():
                self.__dict__[k] = v

        def _wrap_code(self, code: str, wheel_url: httpx.URL) -> str:
            wrapped_code = (
                self.COVERAGE_INIT_CODE
                + "import httpx\n"
                + textwrap.dedent(code)
                + self.COVERAGE_TEARDOWN_CODE
            )
            if wheel_url:
                wrapped_code = (
                    "import pyodide_js as pjs\n"
                    + f"await pjs.loadPackage('{wheel_url}')\n"
                    + wrapped_code
                )
            return wrapped_code

        def run_webworker_with_httpx(self, code: str, wheel_url: httpx.URL) -> None:
            if self.browser == "node":
                pytest.skip("Don't test web-workers in node.js")

            wrapped_code = self._wrap_code(code, wheel_url)
            coverage_out_binary = bytes(self.run_webworker(wrapped_code))
            with open(
                f"{_get_coverage_filename('.coverage.emscripten.')}", "wb"
            ) as outfile:
                outfile.write(coverage_out_binary)

        def run_with_httpx(self: Any, code: str, wheel_url: httpx.URL) -> None:
            if self.browser == "node":
                # stop node.js checking our https certificates
                self.run_js('process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0;')
            wrapped_code = self._wrap_code(code, wheel_url)
            print(wrapped_code)
            coverage_out_binary = bytes(self.run_async(wrapped_code))
            with open(
                f"{_get_coverage_filename('.coverage.emscripten.')}", "wb"
            ) as outfile:
                outfile.write(coverage_out_binary)

    return CoverageRunner(wrapped, has_jspi)


@pytest.fixture()
def pyodide_coverage(
    selenium_with_jspi_if_possible: Any, has_jspi: bool
) -> Generator[Any, None, None]:
    runner = wrapRunner(selenium_with_jspi_if_possible, has_jspi)
    yield runner


@pytest.fixture(scope="session", params=["https", "http"])
def server_url(request, server, https_server):
    if request.param == "https":
        yield https_server.url.copy_with(path="/emscripten")
    else:
        yield server.url.copy_with(path="/emscripten")


@pytest.fixture()
def wheel_url(server_url):
    yield server_url.copy_with(path="/wheel_download/httpx.whl")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate Webassembly Javascript Promise Integration based tests
    only for platforms that support it.

    Currently:
    1) node.js only supports use of JSPI because it doesn't support
    synchronous XMLHttpRequest

    2) firefox doesn't support JSPI

    3) Chrome supports JSPI on or off.
    """
    if "has_jspi" in metafunc.fixturenames:
        if metafunc.config.getoption("--runtime").startswith("node"):
            metafunc.parametrize("has_jspi", [True])
        elif metafunc.config.getoption("--runtime").startswith(
            "firefox"
        ):  # pragma: no cover
            metafunc.parametrize("has_jspi", [False])
        else:
            metafunc.parametrize("has_jspi", [True, False])
