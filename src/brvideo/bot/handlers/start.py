from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command

from brvideo.bot.types import Message

router = Router()


@router.message(Command("start"), F.chat.type == ChatType.PRIVATE)
async def start(message: Message):
    return await message.answer(text="123")
