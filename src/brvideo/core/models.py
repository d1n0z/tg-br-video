from tortoise import Tortoise, fields
from tortoise.models import Model

from brvideo.core import enums
from brvideo.core.config import database_config


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
    await Tortoise.init(database_config)
    await Tortoise.generate_schemas()


async def close():
    await Tortoise.close_connections()
