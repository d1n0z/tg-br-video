import asyncio
from abc import ABC
from typing import Dict, Optional

from brvideo.core.managers.base import BaseCachedModel
from brvideo.core.managers.base.cache import BaseCacheManager
from brvideo.core.managers.base.repository import BaseRepository


class BaseManager(ABC):
    def __init__(
        self,
        repo_cls: Optional[type[BaseRepository]] = None,
        cache_cls: Optional[type[BaseCacheManager]] = None,
        model: Optional[type[BaseCachedModel]] = None,
    ):
        self._lock = asyncio.Lock()
        self._cache: Dict[int, BaseCachedModel] = {}
        self.model = model
        self.repo = repo_cls(self._lock) if repo_cls else None
        self.cache = cache_cls(self._lock, self._cache, self.repo) if cache_cls else None

    async def close(self):
        if self.cache is not None:
            await self.cache.close()

    async def sync(self):
        if self.cache is not None:
            await self.cache.sync()

    async def initialize(self):
        if self.cache is not None:
            await self.cache.initialize()



class BaseEmptyManager(ABC): ...
