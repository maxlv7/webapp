import logging
logging.basicConfig(level=logging.INFO)

import asyncio,os,time,json
from datetime import datetime

from aiohttp import web
from jinja2 import Environment,FileSystemLoader

import orm
from web_frame import add_routes,add_static


def init_jinja2(app,**kw):
    logging.info("init jinja2....")
    options = dict(
        # 是否转义设置为True，就是在渲染模板时自动把变量中的<>&等字符转换为&lt;&gt;&amp;
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),  # 运行代码的开始标识符
        block_end_string=kw.get('block_end_string', '%}'),  # 运行代码的结束标识符
        variable_start_string=kw.get('variable_start_string', '{{'),  # 变量开始标识符
        variable_end_string=kw.get('variable_end_string', '}}'),  # 变量结束标识符
        # Jinja2会在使用Template时检查模板文件的状态，如果模板有修改， 则重新加载模板。如果对性能要求较高，可以将此值设为False
        auto_reload=kw.get('auto_reload', True)
    )

    path = kw.get('path')
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
    logging.info('set jinja2 template path: %s' % path)

    env = Environment(loader=FileSystemLoader(path),**options)

    filters = kw.get('filters')

    if filters is not None:
        for name,f in filters.items():
            env.filters[name] = f

    app['__templating__'] = env

# ------------------------------------------拦截器middlewares设置-------------------------

async def logger_factory(app,handler):
    async def logger(request):
        logging.info("request:%s %s"%(request.method,request.path))
        return await handler(request)
    return logger

async def data_factory(app,handler):
    async def parse_data(request):
        if request.method == "POST":
            if request.content_type.startswith("application/json"):
                request.__date__ = await request.json()
                logging.info("request json：%s"&(request.__data__))
            elif request.content_type.startswith("application/x-www-urlencoded"):
                request.__data__ = await request.post()
        return await handler(request)
    return parse_data

async def response_factory(app,handler):
    async def response(request):
        logging.info("response handler...")

        r = await handler(request)
        logging.info("r = {}".format(str(r)))

        if isinstance(r,web.StreamResponse):
            return r

        if isinstance(r,bytes):
            res = web.Response(body=r)
            res.content_type = "application/octet-stream"
            return res

        if isinstance(r,str):
            if r.startswith("redirect:"):
                return web.HTTPFound(r[9:])
            res = web.Response(body=r.encode("utf-8"))
            res.content_type = "text/html;charset=utf-8"
            return res
        if isinstance(r,dict):
            template = r.get("__template")
            if template is None:
                res = web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda  o:o.__dict__).encode("utf-8"))
                res.content_type = "application/json;charset=utf-8"
                return  res
            else:
                r['__users__'] = request.__user__
                res = web.Response(body=app['__templating__'].get_template(
                    template).render(**r).encode('utf-8'))
                res.content_type = "text/html;charset=utf-8"
                return res
        if isinstance(r,int) and r>=100 and r < 600:
            return web.Response(r)

        if isinstance(r,tuple) and len(r) == 2:
            t,m = r
            if isinstance(t,int) and t>=100 and t < 600:
                return web.Response(status=t,text=str(m))
            res = web.Response(body=str(r).encode("utf-8"))
            res.content_type = "text/plain;charset=utf-8"
            return res
    return response





def datetime_filter(t):
    delta = int(time.time() - t)

    if delta < 60:
        return u'一分钟前'
    if delta <3600:
        return u'%s分钟前'%(delta//3600)
    if delta < 86400:
        return u'%s小时前'%(delta//86400)
    if delta < 604800:
        return u'%s天前'%(delta//86400)

    dt = datetime.fromtimestamp(t)

    return u'%s年%s月%s日'%(dt.year,dt.month,dt.day)


async def init(loop):
    await orm.create_pool(loop=loop,host="localhost",port=3306,user="root",password="root",db="my_blog")
    app = web.Application(loop=loop,middlewares=[logger_factory,response_factory])
    init_jinja2(app,filters=dict(datetime=datetime_filter))

    add_routes(app,"handlers")
    add_static(app)

    srv = await loop.create_server(app.make_handler(),'127.0.0.1',5000)
    logging.info("server run at http://localhost:5000")
    return srv

# 创建一个事件循环对象
loop = asyncio.get_event_loop()

# 把协程注册到事件循环并启动
loop.run_until_complete(init(loop))

loop.run_forever()