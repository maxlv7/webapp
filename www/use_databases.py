import orm
import asyncio
from models import User, Blog, Comment

loop = asyncio.get_event_loop()

async def test():
    await orm.create_pool(loop=loop,user="root",password="root",db="my_blog")

    u = User(name="li",passwd="123123",image="123")

    await u.save()

loop.run_until_complete(test())