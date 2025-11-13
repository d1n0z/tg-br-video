import asyncio
from types import SimpleNamespace


from brvideo.core.managers.admins import AdminManager, _CachedAdmin


def make_row(id: int, nickname: str, tg_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=id, nickname=nickname, tg_id=tg_id)


def test_load_initial_data_success(monkeypatch):
    mgr = AdminManager()

    rows = [make_row(1, "alice", 100), make_row(2, "bob", 200)]

    async def fake_all():
        return rows

    monkeypatch.setattr(mgr.repo, "all", fake_all)

    asyncio.run(mgr.cache.load_initial_data())

    # cache populated by DB ids
    assert 1 in mgr._cache and 2 in mgr._cache
    assert mgr._cache[1].nickname == "alice"
    assert mgr._cache[2].tg_id == 200


def test_load_initial_data_typeerror_is_handled(monkeypatch):
    mgr = AdminManager()

    # Create a row missing tg_id to provoke TypeError when constructing model
    bad_row = SimpleNamespace(id=3, nickname="charlie")

    async def fake_all():
        return [bad_row]

    monkeypatch.setattr(mgr.repo, "all", fake_all)

    # Should not raise, and cache should not contain the bad id
    asyncio.run(mgr.cache.load_initial_data())
    assert 3 not in mgr._cache


def test_add_admin_new_and_existing(monkeypatch):
    mgr = AdminManager()

    row = make_row(10, "newadmin", 12345)

    async def fake_ensure_admin(*args, **kwargs):
        return row, True

    monkeypatch.setattr(mgr.repo, "ensure_admin", fake_ensure_admin)

    # add new
    admin = asyncio.run(mgr.cache.add_admin(tg_id=12345, nickname="newadmin"))
    assert admin.id == 10
    assert 10 in mgr._cache
    assert 10 in mgr.cache._dirty

    # second add should return existing cache entry (no duplication)
    admin2 = asyncio.run(mgr.cache.add_admin(tg_id=12345, nickname="newadmin"))
    assert admin2 is mgr._cache[10]


def test_del_admin_found_and_not_found():
    mgr = AdminManager()

    # populate cache manually
    cached = _CachedAdmin.model_validate(
        {"id": 7, "nickname": "to_delete", "tg_id": 777}
    )
    mgr._cache[7] = cached

    removed = asyncio.run(mgr.cache.del_admin(tg_id=777))
    assert removed is not None
    assert 7 not in mgr._cache
    assert 7 in mgr.cache._dirty

    # deleting non-existing tg id returns None
    none = asyncio.run(mgr.cache.del_admin(tg_id=999))
    assert none is None


def test_edit_admin_updates_and_marks_dirty(monkeypatch):
    mgr = AdminManager()

    row = make_row(20, "old", 555)

    async def fake_ensure_admin(*args, **kwargs):
        return row, False

    monkeypatch.setattr(mgr.repo, "ensure_admin", fake_ensure_admin)

    edited = asyncio.run(mgr.cache.edit_admin(tg_id=555, nickname="newname"))
    assert edited is not None
    assert edited.nickname == "newname"
    assert 20 in mgr._cache
    assert mgr._cache[20].nickname == "newname"
    assert 20 in mgr.cache._dirty


def test_is_admin_true_and_false():
    mgr = AdminManager()
    mgr._cache[99] = _CachedAdmin.model_validate(
        {"id": 99, "nickname": "x", "tg_id": 4242}
    )

    assert asyncio.run(mgr.cache.is_admin(4242)) is True
    assert asyncio.run(mgr.cache.is_admin(1111)) is False


def test_sync_updates_and_creates(monkeypatch):
    mgr = AdminManager()

    # Prepare two cached items in cache keyed by DB id
    mgr._cache.clear()
    a = _CachedAdmin.model_validate({"id": 1, "nickname": "Alice", "tg_id": 100})
    b = _CachedAdmin.model_validate({"id": 2, "nickname": "Bob", "tg_id": 200})
    mgr._cache[1] = a
    mgr._cache[2] = b
    mgr.cache._dirty.update({1, 2})

    # Admins.filter will report that only id 1 exists in DB and has old nickname
    existing_row = make_row(1, "OldAlice", 100)

    async def fake_filter(**kwargs):
        # return only existing rows
        return [existing_row]

    bulk_updated = {}

    async def fake_bulk_update(rows, fields=None, batch_size=None):
        # record that we attempted to update
        bulk_updated["updated"] = [r.id for r in rows]

    bulk_created = {}

    async def fake_bulk_create(items, batch_size=None):
        bulk_created["created_count"] = len(items)

    # Patch the Admins methods used in sync
    import sys

    admins_mod = sys.modules["brvideo.core.managers.admins"]

    monkeypatch.setattr(
        admins_mod,
        "Admins",
        SimpleNamespace(
            filter=fake_filter,
            bulk_update=fake_bulk_update,
            bulk_create=fake_bulk_create,
        ),
        raising=False,
    )

    # Run sync
    asyncio.run(mgr.cache.sync(batch_size=10))

    # After sync, bulk_update should have been called for id 1 and bulk_create for id 2
    assert bulk_updated.get("updated") == [1]
    assert bulk_created.get("created_count") == 1
    # Dirty set should be cleared for those ids
    assert 1 not in mgr.cache._dirty
    assert 2 not in mgr.cache._dirty


def test_sync_handles_exception_and_keeps_dirty(monkeypatch):
    mgr = AdminManager()

    mgr._cache.clear()
    c = _CachedAdmin.model_validate({"id": 11, "nickname": "C", "tg_id": 11})
    mgr._cache[11] = c
    mgr.cache._dirty.add(11)

    async def fake_filter(**kwargs):
        raise RuntimeError("boom")

    import sys

    admins_mod = sys.modules["brvideo.core.managers.admins"]
    monkeypatch.setattr(
        admins_mod, "Admins", SimpleNamespace(filter=fake_filter), raising=False
    )

    # Should not raise, but dirty should remain
    asyncio.run(mgr.cache.sync())
    assert 11 in mgr.cache._dirty


def test_sync_early_return_when_dirty_empty(monkeypatch):
    mgr = AdminManager()

    # Ensure dirty is empty
    mgr.cache._dirty.clear()

    # Patch Admins.filter to raise if called
    import sys

    admins_mod = sys.modules["brvideo.core.managers.admins"]

    async def bad_filter(**kwargs):
        raise AssertionError("Admins.filter should not be called when dirty is empty")

    monkeypatch.setattr(
        admins_mod, "Admins", SimpleNamespace(filter=bad_filter), raising=False
    )

    # Should return cleanly
    asyncio.run(mgr.cache.sync())


def test_sync_payloads_empty_if_cache_missing_ids(monkeypatch):
    mgr = AdminManager()

    # Put an id into dirty that is not in the cache
    mgr.cache._dirty.clear()
    mgr.cache._dirty.add(9999)

    import sys

    admins_mod = sys.modules["brvideo.core.managers.admins"]

    async def bad_filter(**kwargs):
        raise AssertionError("Admins.filter should not be called when payloads empty")

    monkeypatch.setattr(
        admins_mod, "Admins", SimpleNamespace(filter=bad_filter), raising=False
    )

    asyncio.run(mgr.cache.sync())
    # dirty should remain since nothing changed
    assert 9999 in mgr.cache._dirty


def test_sync_no_updates_when_rows_match(monkeypatch):
    mgr = AdminManager()

    mgr._cache.clear()
    a = _CachedAdmin.model_validate({"id": 1, "nickname": "Same", "tg_id": 10})
    mgr._cache[1] = a
    mgr.cache._dirty.add(1)

    existing_row = make_row(1, "Same", 10)

    async def fake_filter(**kwargs):
        return [existing_row]

    # bulk operations should not be called
    async def fail_update(*args, **kwargs):
        raise AssertionError("bulk_update should not be called when nothing changed")

    async def fail_create(*args, **kwargs):
        raise AssertionError("bulk_create should not be called when nothing changed")

    import sys

    admins_mod = sys.modules["brvideo.core.managers.admins"]
    monkeypatch.setattr(
        admins_mod,
        "Admins",
        SimpleNamespace(
            filter=fake_filter, bulk_update=fail_update, bulk_create=fail_create
        ),
        raising=False,
    )

    asyncio.run(mgr.cache.sync())
    assert 1 not in mgr.cache._dirty


def test_sync_batch_splitting(monkeypatch):
    mgr = AdminManager()

    mgr._cache.clear()
    # three items to force two batches when batch_size=2
    for i in (1, 2, 3):
        mgr._cache[i] = _CachedAdmin.model_validate(
            {"id": i, "nickname": f"n{i}", "tg_id": i * 10}
        )
    mgr.cache._dirty.update({1, 2, 3})

    # make filter return rows for 1 and 3; make id=1 have different nickname so it will be updated
    existing_rows = [make_row(1, "old_n1", 10), make_row(3, "n3", 30)]

    async def fake_filter(**kwargs):
        return [r for r in existing_rows if r.id in kwargs.get("id__in", [])]

    bulk_updates = []

    async def fake_bulk_update(rows, fields=None, batch_size=None):
        bulk_updates.append([r.id for r in rows])

    bulk_creates = []

    async def fake_bulk_create(items, batch_size=None):
        # items are pydantic models in current implementation; record their ids
        bulk_creates.append([getattr(i, "id", None) for i in items])

    import sys

    admins_mod = sys.modules["brvideo.core.managers.admins"]
    monkeypatch.setattr(
        admins_mod,
        "Admins",
        SimpleNamespace(
            filter=fake_filter,
            bulk_update=fake_bulk_update,
            bulk_create=fake_bulk_create,
        ),
        raising=False,
    )

    asyncio.run(mgr.cache.sync(batch_size=2))

    # Expect at least one update and one create across batches
    assert any(1 in batch for batch in bulk_updates)
    assert (
        any(2 in batch for batch in bulk_creates)
        or any(3 in batch for batch in bulk_creates)
        or bulk_creates
    )
