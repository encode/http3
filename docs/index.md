# HTTP3

<a href="https://travis-ci.org/encode/http3">
    <img src="https://travis-ci.org/encode/http3.svg?branch=master" alt="Build Status">
</a>
<a href="https://codecov.io/gh/encode/http3">
    <img src="https://codecov.io/gh/encode/http3/branch/master/graph/badge.svg" alt="Coverage">
</a>
<a href="https://pypi.org/project/http3/">
    <img src="https://badge.fury.io/py/http3.svg" alt="Package version">
</a>

HTTP3 is a next-generation HTTP client for Python.

---

```python
>>> r = http3.get('https://www.example.org/')
>>> r.status_code
<StatusCode.OK: 200>
>>> r.protocol
'HTTP/2'
>>> r.headers['content-type']
'text/html; charset=UTF-8'
>>> r.text
'<!doctype html>\n<html>\n<head>\n    <title>Example Domain</title>...'
```

## Features

HTTP3 builds on the well-established usability of `requests`, and gives you:

* A requests-compatible API.
* HTTP/2 and HTTP/1.1 support.
* Standard synchronous interface, but with `async`/`await` support if you need it.
* Strict timeouts everywhere.
* Fully type annotated.
* 100% test coverage.

## User Guide

This part of the documentation will walk you through all of the functionality
in HTTP3:

* QuickStart
  * Make a Request
  * Passing Parameters in URLs
  * Response Content
  * Binary Response Content
  * JSON Response Content
  * Raw Response Content
  * Custom Headers
  * More complicated POST requests
  * POST a Multipart-Encoded File
  * Response Status Codes
  * Response Headers
  * Cookies
  * Redirection and History
  * Timeouts
  * Errors and Exceptions
* Parallel Requests
  * Making Parallel Requests
  * Exceptions and Cancellations
  * Parallel requests with a Client
  * Async parallel requests
* Async Client
  * Making Async requests
  * API Differences
* Requests Compatibility Guide
  * Overview
  * API Differences

## Developer Interface

This part of the documentation provides a complete API reference:

* Main API
* Exceptions
* Client
* Response
* Request
* Data Structures
  * URL
  * Origin
  * Headers
  * Cookies
* Parallel Requests
  * ParallelManager
  * PendingResponse
* Custom Dispatch
  * Dispatcher
* Async API
  * AsyncClient
  * AsyncResponse
  * AsyncRequest
  * AsyncParallelManager
  * AsyncPendingResponse
  * AsyncDispatcher
