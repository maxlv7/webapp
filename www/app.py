import asyncio
from aiohttp import web

async def index(request):
    return web.Response(body="<h1>Hahahaha</h1>",content_type="text/html")

async def init(loop):
    app = web.Application()
    app.router.add_route("GET","/",index)
    # web.run_app(app=app,host="localhost",port=5000)
    srv = await loop.create_server(app.make_handler(),"127.0.0.1",5000)
    print("Service run in: http://localhost:5000 ")
    # return srv
# 创建一个事件循环对象
loop = asyncio.get_event_loop()

# 把协程注册到事件循环并启动
loop.run_until_complete(init(loop))

loop.run_forever()