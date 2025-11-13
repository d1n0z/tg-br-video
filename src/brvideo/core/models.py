from tortoise import Tortoise, fields
from tortoise.models import Model

try:
    from brvideo.core import enums
except ImportError:  # `aerich init` and `aerich init-db` must be run from root, not from src
    from src.brvideo.core import enums

class Applications(Model):
    id = fields.IntField(primary_key=True)
    nickname = fields.CharField(max_length=50)
    server = fields.IntField()
    social = fields.CharEnumField(enum_type=enums.Socials, max_length=255)
    date = fields.DatetimeField(auto_now_add=True)
    link_acc = fields.TextField()
    accepted = fields.BooleanField()
    reason = fields.TextField(null=True)

    class Meta:
        table = "applications"


class Admins(Model):
    id = fields.IntField(primary_key=True)
    nickname = fields.CharField(max_length=50)
    tg_id = fields.BigIntField()

    class Meta:
        table = "admins"


async def init():
    from brvideo.core.config import database_config

    await Tortoise.init(database_config)
    await Tortoise.generate_schemas()


async def close():
    await Tortoise.close_connections()
