"""Resource managers for plone-client."""

from .base import BaseManager
from .blocks import BlocksManager
from .content import ContentManager
from .content_extras import CommentsManager
from .content_extras import HistoryManager
from .content_extras import TilesManager
from .database import DatabaseManager
from .files import FilesManager
from .relations import RelationsManager
from .search import SearchManager
from .system import AddonsManager
from .system import ControlpanelsManager
from .system import RegistryManager
from .system import SiteManager
from .users import GroupsManager
from .users import SharingManager
from .users import UsersManager
from .utilities import UtilitiesManager
from .workingcopy import WorkingCopyManager


__all__ = [
    "AddonsManager",
    "BaseManager",
    "BlocksManager",
    "CommentsManager",
    "ContentManager",
    "ControlpanelsManager",
    "DatabaseManager",
    "FilesManager",
    "GroupsManager",
    "HistoryManager",
    "RegistryManager",
    "RelationsManager",
    "SearchManager",
    "SharingManager",
    "SiteManager",
    "TilesManager",
    "UsersManager",
    "UtilitiesManager",
    "WorkingCopyManager",
]
