import copy
from typing import Dict, List, Optional

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
    async def ensure_admin(tg_id: int, **defaults) -> tuple[Admins, bool]:
        return await Admins.get_or_create(tg_id=tg_id, defaults=defaults)

    @staticmethod
    async def all() -> List[Admins]:
        return await Admins.all()


class AdminCacheManager(BaseCacheManager):
    repo: AdminRepository
    _cache: Dict[int, _CachedAdmin]

    async def sync(self, batch_size: int = 1000):
        async with self._lock:
            if not self._dirty:
                return
            dirty_snapshot = set(self._dirty)
            payloads = {
                tg: copy.deepcopy(self._cache[tg])
                for tg in dirty_snapshot
                if tg in self._cache
            }

        if not payloads:
            return

        items = list(payloads.items())
        try:
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                ids = [id for id, _ in batch]

                existing_rows = await Admins.filter(id__in=ids)
                existing_map = {row.id: row for row in existing_rows}

                to_update = []
                to_create = []
                for tg, cached in batch:
                    if tg in existing_map:
                        row = existing_map[tg]
                        dirty = False
                        for field in _CachedAdmin.model_fields.keys():
                            val = getattr(cached, field)
                            row_val = getattr(
                                row, field, getattr(row, f"{field}", None)
                            )
                            if row_val != val:
                                setattr(row, field, val)
                                dirty = True
                        if dirty:
                            to_update.append(row)
                    else:
                        to_create.append(_CachedAdmin.from_model(cached))

                if to_update:
                    await Admins.bulk_update(
                        to_update,
                        fields=_CachedAdmin.model_fields.keys(),
                        batch_size=batch_size,
                    )
                if to_create:
                    await Admins.bulk_create(to_create, batch_size=batch_size)

        except Exception:
            loguru.logger.exception("User sync failed")
            return

        async with self._lock:
            for tg, old_val in payloads.items():
                cur = self._cache.get(tg)
                if cur is None:
                    self._dirty.discard(tg)
                    continue
                if cur.__dict__ == old_val.__dict__:
                    self._dirty.discard(tg)

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

    async def add_admin(self, tg_id: int, nickname: str) -> _CachedAdmin:
        row, _ = await self.repo.ensure_admin(tg_id=tg_id, nickname=nickname)
        admin = _CachedAdmin.from_model(row)
        async with self._lock:
            if row.id in self._cache:
                return self._cache[row.id]
            self._cache[admin.id] = admin
            self._dirty.add(admin.id)
        return admin

    async def del_admin(self, tg_id: int) -> Optional[_CachedAdmin]:
        async with self._lock:
            admin = next(
                (admin for admin in self._cache.values() if admin.tg_id == tg_id),
                None,
            )
            if admin:
                self._cache.pop(admin.id)
                self._dirty.add(admin.id)
        return admin

    async def edit_admin(self, tg_id: int, **fields) -> Optional[_CachedAdmin]:
        row, _ = await self.repo.ensure_admin(tg_id=tg_id, defaults=fields)
        admin = _CachedAdmin.from_model(row)
        async with self._lock:
            for field, val in fields.items():
                setattr(admin, field, val)
            self._cache[admin.id] = admin
            self._dirty.add(admin.id)
        return admin

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

        self.add_admin = self.cache.add_admin
        self.del_admin = self.cache.del_admin
        self.edit_admin = self.cache.edit_admin
        self.is_admin = self.cache.is_admin
