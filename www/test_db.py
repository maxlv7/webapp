import orm, asyncio
from models import User, Blog, Comment

loop = asyncio.get_event_loop()
async def test():
	await orm.create_pool(loop, user='root', password='root', db='my_blog')
	u = User(id="1",name='Li', email='admin@maxlv.org', passwd='123456', image='about:blank')
	await u.save()


loop.run_until_complete(test())
# loop.close()
