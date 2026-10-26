from plone_client import exceptions

import httpx
import pytest


def _response(status: int, **kwargs) -> httpx.Response:
    request = httpx.Request("GET", "http://plone.test/Plone/++api++/doc")
    return httpx.Response(status, request=request, **kwargs)


@pytest.mark.parametrize(
    "status,expected",
    [
        (400, exceptions.PloneBadRequestError),
        (401, exceptions.PloneAuthenticationError),
        (403, exceptions.PloneForbiddenError),
        (404, exceptions.PloneNotFoundError),
        (409, exceptions.PloneConflictError),
        (412, exceptions.PloneAPIError),
        (500, exceptions.PloneServerError),
        (503, exceptions.PloneServerError),
    ],
)
def test_error_class_by_status(status, expected):
    error = exceptions.error_from_response(_response(status, json={}))
    assert type(error) is expected
    assert error.status_code == status


@pytest.mark.parametrize(
    "body,message,error_type",
    [
        (
            {"type": "NotFound", "message": "Resource not found"},
            "Resource not found",
            "NotFound",
        ),
        (
            {
                "error": {
                    "type": "BadRequest",
                    "message": "Property '@type' is required",
                }
            },
            "Property '@type' is required",
            "BadRequest",
        ),
        ({}, "Not Found", ""),
    ],
)
def test_error_details_from_json(body, message, error_type):
    error = exceptions.error_from_response(_response(404, json=body))
    assert error.message == message
    assert error.error_type == error_type
    assert error.body == body


def test_error_details_from_text():
    error = exceptions.error_from_response(_response(502, text="Bad gateway\n"))
    assert error.message == "Bad gateway"
    assert error.body == "Bad gateway\n"


def test_error_str_and_dict():
    error = exceptions.error_from_response(
        _response(404, json={"type": "NotFound", "message": "Gone"})
    )
    assert str(error) == "GET http://plone.test/Plone/++api++/doc: HTTP 404 Gone"
    assert error.to_dict() == {
        "status_code": 404,
        "type": "NotFound",
        "message": "Gone",
        "method": "GET",
        "url": "http://plone.test/Plone/++api++/doc",
    }


@pytest.mark.parametrize(
    "error_class",
    [
        exceptions.PloneAPIError,
        exceptions.PloneConfigurationError,
        exceptions.PloneConnectionError,
        exceptions.PloneReadOnlyError,
        exceptions.PloneTimeoutError,
    ],
)
def test_every_error_is_a_client_error(error_class):
    assert issubclass(error_class, exceptions.PloneClientError)
