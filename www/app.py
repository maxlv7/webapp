import logging
logging.basicConfig(level=logging.INFO)

import asyncio,os,time,json
from datetime import datetime

from aiohttp import web
from jinja2 import Environment,FileSystemLoader

import orm
from web_frame import add_routes,add_static

from handlers import cookie2user, COOKIE_NAME

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
    logging.info("logger factory run...")
    async def logger(request):
        logging.info("request:%s %s"%(request.method,request.path))
        # 日志记录完之后，调用传入的handler继续处理请求
        return await handler(request)
    return logger

async def data_factory(app,handler):
    logging.info("data factory run...")
    async def parse_data(request):
        if request.method == "POST":
            if request.content_type.startswith('application/json'):
                request.__date__ = await request.json()
                logging.info("request json：%s"&(request.__data__))
            elif request.content_type.startswith("application/x-www-urlencoded"):
                request.__data__ = await request.post()
        return await handler(request)
    return parse_data

# 在处理请求之前,先将cookie解析出来,并将登录用于绑定到request对象上
# 这样后续的url处理函数就可以直接拿到登录用户
# 以后的每个请求,都是在这个middle之后处理的,都已经绑定了用户信息
async def auth_factory(app,handler):
    logging.info("auth factory run...")
    async def auth(request):
        logging.info("check user: %s %s" % (request.method, request.path))
        request.__user__ = None # 先绑定一个None到请求的__user__属性
        cookie_str = request.cookies.get(COOKIE_NAME)

        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logging.info("set current user: %s" % user.email)
                request.__user__ = user # 将用户信息绑定到请求上
            if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
                return web.HTTPFound('/signin')
        return await handler(request)
    return auth



#将request handler的返回值转换为web.Response对象
async def response_factory(app,handler):
    logging.info("response factory run...")
    async def response(request):
        logging.info("response handler...")
        logging.info("request = {}".format(request))
        # logging.info("request type = {}".format(type(request)))
        # logging.info("handler name = {}".format(handler.__name__))

        # 调用handler来处理请求，并返回响应结果
        # 这个handler就是RequestHandler的实例
        r = await handler(request)

        logging.info("r == {}".format(str(r)))

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
            template = r.get("__template__")
            if template is None:
                res = web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda  o:o.__dict__).encode("utf-8"))
                res.content_type = "application/json;charset=utf-8"
                return  res
            else:
                r['__users__'] = request.__user__ # 增加__user__,前端页面将依次来决定是否显示评论框
                # r['__users__'] = "11111"# 增加__user__,前端页面将依次来决定是否显示评论框
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
# ------------------------------------------拦截器middlewares设置-------------------------

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

    app = web.Application(loop=loop,middlewares=[logger_factory,auth_factory,response_factory])

    # 设置模板为jiaja2, 并以时间为过滤器
    init_jinja2(app,filters=dict(datetime=datetime_filter))

    # 注册所有url处理函数
    add_routes(app,"handlers")

    # 将当前目录下的static目录添加到app目录
    add_static(app)

    srv = await loop.create_server(app.make_handler(),'127.0.0.1',5000)
    logging.info("server run at http://localhost:5000")
    return srv

# 创建一个事件循环对象
loop = asyncio.get_event_loop()

# 把协程注册到事件循环并启动
loop.run_until_complete(init(loop))

loop.run_forever()