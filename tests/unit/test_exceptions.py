"""Unit tests for exception hierarchy."""

from __future__ import annotations

from plone_client.exceptions import PloneAPIError
from plone_client.exceptions import PloneAuthenticationError
from plone_client.exceptions import PloneClientError
from plone_client.exceptions import PloneConflictError
from plone_client.exceptions import PloneConnectionError
from plone_client.exceptions import PloneForbiddenError
from plone_client.exceptions import PloneNotFoundError
from plone_client.exceptions import PloneServerError
from plone_client.exceptions import PloneTimeoutError

import pytest


@pytest.mark.unit
class TestExceptionHierarchy:
    def test_all_inherit_from_base(self) -> None:
        for exc_class in (
            PloneAPIError,
            PloneAuthenticationError,
            PloneConflictError,
            PloneConnectionError,
            PloneForbiddenError,
            PloneNotFoundError,
            PloneServerError,
            PloneTimeoutError,
        ):
            assert issubclass(exc_class, PloneClientError)

    def test_api_error_stores_metadata(self) -> None:
        err = PloneAPIError("oops", status_code=422, response_body={"field": "title"})
        assert err.status_code == 422
        assert err.response_body == {"field": "title"}
        assert str(err) == "oops"

    def test_api_error_defaults(self) -> None:
        err = PloneAPIError("fail")
        assert err.status_code is None
        assert err.response_body is None

    def test_catch_as_base(self) -> None:
        with pytest.raises(PloneClientError):
            raise PloneNotFoundError("not found")
