from brvideo.core.managers.admins import AdminManager

to_init = [
    admins := AdminManager(),
]


async def initialize():
    for manager in to_init:
        await manager.initialize()


async def close():
    for manager in to_init:
        await manager.sync()
        await manager.close()
