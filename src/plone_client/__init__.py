"""plone-client: a Python library and command line client for Plone sites.

Example::

    from plone_client import PloneClient

    with PloneClient.from_profile("blog") as site:
        page = site.content.get("/about")
        site.workflow.transition("/about", "publish")
"""

from .auth import JWTAuth
from .auth import TokenAuth
from .client import PloneClient
from .exceptions import PloneAPIError
from .exceptions import PloneAuthenticationError
from .exceptions import PloneBadRequestError
from .exceptions import PloneClientError
from .exceptions import PloneConfigurationError
from .exceptions import PloneConflictError
from .exceptions import PloneConnectionError
from .exceptions import PloneForbiddenError
from .exceptions import PloneNotFoundError
from .exceptions import PloneOperationError
from .exceptions import PloneReadOnlyError
from .exceptions import PloneServerError
from .exceptions import PloneTimeoutError
from .managers.files import file_data


__version__ = "1.0.0a2.dev0"

__all__ = [
    "JWTAuth",
    "PloneAPIError",
    "PloneAuthenticationError",
    "PloneBadRequestError",
    "PloneClient",
    "PloneClientError",
    "PloneConfigurationError",
    "PloneConflictError",
    "PloneConnectionError",
    "PloneForbiddenError",
    "PloneNotFoundError",
    "PloneOperationError",
    "PloneReadOnlyError",
    "PloneServerError",
    "PloneTimeoutError",
    "TokenAuth",
    "file_data",
]
