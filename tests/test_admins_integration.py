import asyncio
from tortoise import Tortoise

from brvideo.core.managers.admins import AdminManager
from brvideo.core.models import Admins


def test_integration_add_edit_sync():
    async def _run():
        # init tortoise with our models
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["brvideo.core.models"]}
        )
        await Tortoise.generate_schemas()

        mgr = AdminManager()

        # add admin via manager -> should create DB row
        admin = await mgr.add_admin(tg_id=999999, nickname="int_user")
        assert admin.id is not None

        # verify DB row exists
        row = await Admins.get(tg_id=999999)
        assert row.nickname == "int_user"

        # edit via manager and sync
        await mgr.edit_admin(tg_id=999999, nickname="int_user2")
        # sync will persist changes to DB
        await mgr.cache.sync()

        row2 = await Admins.get(tg_id=999999)
        assert row2.nickname == "int_user2"

        await Tortoise.close_connections()

    asyncio.run(_run())
