from typing import Dict, List

import loguru

from brvideo.core.managers.base import (
    BaseCachedModel,
    BaseCacheManager,
    BaseManager,
    BaseRepository,
)
from brvideo.core.models import Admins


class _CachedAdmin(BaseCachedModel):
    id: int
    nickname: str
    tg_id: int


class AdminRepository(BaseRepository):
    @staticmethod
    async def all() -> List[Admins]:
        return await Admins.all()


class AdminCacheManager(BaseCacheManager):
    repo: AdminRepository
    _cache: Dict[int, _CachedAdmin]

    async def sync(self):
        ...  # TODO

    async def load_initial_data(self):
        if not self.repo:
            return
        rows = await self.repo.all()
        async with self._lock:
            for row in rows:
                try:
                    self._cache[row.id] = _CachedAdmin.from_model(row)
                except TypeError:
                    loguru.logger.exception("Error loading Admins into cache")

    async def is_admin(self, tg_id: int) -> bool:
        async with self._lock:
            return next(
                (True for admin in self._cache.values() if admin.tg_id == tg_id),
                False,
            )


class AdminManager(BaseManager):
    repo: AdminRepository
    cache: AdminCacheManager
    _cache: Dict[int, _CachedAdmin]

    def __init__(self):
        super().__init__(
            repo_cls=AdminRepository,
            cache_cls=AdminCacheManager,
            model=_CachedAdmin,
        )

        self.is_admin = self.cache.is_admin
