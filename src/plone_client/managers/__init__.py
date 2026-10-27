"""Managers: the areas of ``plone.restapi``, as attributes of the client."""

from .base import BaseManager
from .block_types import BlockTypesManager
from .content import ContentManager
from .discussion import AliasesManager
from .discussion import CommentsManager
from .discussion import RelationsManager
from .discussion import TranslationsManager
from .files import FilesManager
from .navigation import NavigationManager
from .search import QuerystringManager
from .search import SearchManager
from .site import AddonsManager
from .site import ContentRulesManager
from .site import ControlpanelsManager
from .site import RegistryManager
from .site import SystemManager
from .types import TypesManager
from .types import VocabulariesManager
from .users import GroupsManager
from .users import SharingManager
from .users import UsersManager
from .workflow import HistoryManager
from .workflow import WorkflowManager
from .workflow import WorkingCopyManager


__all__ = [
    "AddonsManager",
    "AliasesManager",
    "BaseManager",
    "BlockTypesManager",
    "CommentsManager",
    "ContentManager",
    "ContentRulesManager",
    "ControlpanelsManager",
    "FilesManager",
    "GroupsManager",
    "HistoryManager",
    "NavigationManager",
    "QuerystringManager",
    "RegistryManager",
    "RelationsManager",
    "SearchManager",
    "SharingManager",
    "SystemManager",
    "TranslationsManager",
    "TypesManager",
    "UsersManager",
    "VocabulariesManager",
    "WorkflowManager",
    "WorkingCopyManager",
]
