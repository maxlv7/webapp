import orm, asyncio
from models import User, Blog, Comment
import time

# loop = asyncio.get_event_loop()
# async def test():
# 	await orm.create_pool(loop, user='root', password='root', db='my_blog')
# 	u = User(id="2",name='Li', email='2@maxlv.org', passwd='123456', image='about:blank')
# 	await u.save()
loop = asyncio.get_event_loop()
async def test():
	await orm.create_pool(loop, user='root', password='root', db='my_blog')
	summary = "test test test "
	u = Blog(id="2",user_id="2",user_name="2" ,user_image="2",content="123",name='test',summary=summary,created_at=time.time()-120 )
	await u.save()


loop.run_until_complete(test())
# loop.close()
