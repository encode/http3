import pickle

from httpx import HTTPStatusError, RequestError


def test_pickle():
    req_err = RequestError("hi!", request="request")  # type:ignore[arg-type]
    req_err_clone = pickle.loads(pickle.dumps(req_err))
    assert req_err.args == req_err_clone.args
    assert req_err.request == req_err_clone.request

    status_err = HTTPStatusError("hi", request="request", response="response")  # type:ignore[arg-type]
    status_err_clone = pickle.loads(pickle.dumps(status_err))
    assert status_err.args == status_err_clone.args
    assert status_err.request == status_err_clone.request
    assert status_err.response == status_err_clone.response
