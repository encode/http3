---
template: pyodide.html
---
# Emscripten Support

httpx has support for running on Webassembly / Emscripten using [pyodide](https://github.com/pyodide/pyodide/). 

In Emscripten, all network connections are handled by the enclosing Javascript runtime. As such, there is limited control over various features. In particular:

- Proxy servers are handled by the runtime, so you cannot control them.
- httpx has no control over connection pooling.
- Certificate handling is done by the browser, so you cannot modify it.
- Requests are constrained by cross-origin isolation settings in the same way as any request that is originated by Javascript code.
- On browsers, timeouts will not work in the main browser thread unless your browser supports [Javascript Promise Integration](https://github.com/WebAssembly/js-promise-integration/blob/main/proposals/js-promise-integration/Overview.md). This is currently behind a flag on chrome, and not yet supported by non-chromium browsers.
- On node.js, synchronous requests will only work if you enable Javascript Promise Integration. You can do this using the `--experimental-wasm-stack-switching` flag when you run the node executable.

## Try it in your browser

Use the following live example to test httpx in your web browser. You can change the code below and hit run again to test different features or web addresses.

<div id="pyodide_buttons"></div>

<div id="pyodide_output">
</div>

<div id="pyodide_editor">
import httpx
print("Sending response using httpx in the browser:")
print("--------------------------------------------")
r=httpx.get("http://www.example.com")
print("Status = ",r.status_code)
print("Response = ",r.text[:50],"...")
</div>


## Build it
Because this is a pure python module, building is the same as ever (`python -m build`), or use the built wheel from pypi.

## Testing Custom Builds of httpx in Emscripten
Once you have a wheel you can test it in your browser. You can do this using the [pyodide console](
https://pyodide.org/en/latest/console.html), or by hosting your own web page. 

1) To test in pyodide console, serve the wheel file via http (e.g. by calling python -m `http.server` in the dist directory.) Then in the [pyodide console](
https://pyodide.org/en/latest/console.html), type the following, replacing the URL of the locally served wheel.

```
import pyodide_js as pjs
import ssl,certifi,idna
pjs.loadPackage("<URL_OF_THE_WHEEL>")
import httpx
# Now httpx should work
```

2) To test a custom built wheel in your own web page, create a page which loads the pyodide javascript (see the [instructions](https://pyodide.org/en/stable/usage/index.html) on the pyodide website), then call `pyodide.loadPackage` on your pyodide instance, pointing it at the wheel file. Then make sure you load the dependencies by loading the ssl,certifi and idna packages (which are part of pyodide - call `pyodide.loadPackage` for each one and pass it just the package name.)

3) To test in node.js, make sure you have a  pyodide distribution downloaded to a known folder, then load pyodide following the instructions on the pyodide website (https://pyodide.org/en/stable/usage/index.html). You can then call await `pyodide.loadPackage('<wheel location>');` and httpx should be available as a package in pyodide. You need at version 0.26.2 or later of pyodide.

