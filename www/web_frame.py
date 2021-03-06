import asyncio,os,inspect,logging,functools

from urllib import parse

from aiohttp import web

logging.basicConfig(level=logging.INFO)

# 定义get装饰器

def get(path):
    """
    @get('/path')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            return func(*args,**kwargs)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 定义post装饰器

def post(path):
    """
    @post('/path')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kwargs):
            return func(*args,**kwargs)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 获取函数值为空的命名关键字
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters

    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

# 获取命名关键字参数名
def get_named_kw_args(fn):
    # 如果url处理函数需要传入关键字参数，获取这个key
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

# 判断函数fn是否带有命名关键字参数
def has_named_kw_args(fn):  # 判断是否有指定命名关键字参数
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

# 判断函数fn是否带有关键字参数
def has_var_kw_arg(fn):  # 判断是否有关键字参数，VAR_KEYWORD对应**kw
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 函数fn是否有请求关键字
# 判断是否存在一个参数叫做request，并且该参数要在其他普通的位置参数之后，即属于*kw或者**kw或者*或者*args之后的参数
def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        # 只能是位置参数POSITIONAL_ONLY
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (
                fn.__name__, str(sig)))
    return found

#定义RequestHandler类，封装url处理函数
# RequestHandler的目的是从url函数中分析需要提取的参数
# 调用url参数，将结果转换为web.Response
class RequestHandler(object):
    def __init__(self,app,fn):
        self._app = app #web application
        self._func = fn #handler
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    # 定义了__call__，其实例可以被视为函数
    async def __call__(self, request):
        logging.info("通过call被调用。。。")
        kw = None

        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest("missing content type...")
                ct = request.content_type.lower()
                if ct.startswith("application/json"):
                    params = await request.json()

                    if not isinstance(params,dict):
                        return web.HTTPBadRequest("json body must be object!")
                    kw = params

                elif ct.startswith("application/x-www-form-urlencoded") or ct.startswith1("multipart/for-data"):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest("unsupported content-type:{}".format(request.content_type))
            if request.method == "get":
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy

            for k,v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)

                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        if self._required_kw_args:
            for name in self._required_kw_args:
                if name not in kw:
                    logging.info("name === %s"%name)
                    return web.HTTPBadRequest()
                    # return web.HTTPBadRequest("miss argument:%s"%name)

        logging.info("call with args:%s"%str(kw))

        try:
            r = await self._func(**kw)
            return r
        except:
            pass

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/',path)

    logging.info("add static %s ==> %s"%('/static/',path))

def add_route(app,fn):
    method = getattr(fn,'__method__')
    path = getattr(fn,'__route__')

    if path is None or method is None:
        raise ValueError("@get or @post not define in {} ".format(str(fn)))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)

    logging.info("---> add route %s %s => %s(%s)" % (method, path, fn.__name__, '. '.join(inspect.signature(fn).parameters.keys())))
    # 注册request handler
    # RequestHandle类中有__callable__方法，因此RequestHandler(app, fn)
    # 相当于创建了一个url处理函数，函数名就是fn
    app.router.add_route(method,path,RequestHandler(app,fn))

    # logging.info("add route %s %s %s"%(method,path,RequestHandler(app,fn)))


def add_routes(app,module_name):
    n = module_name.rfind('.')
    logging.info("n = {}".format(n))
    if n == (-1):
        mod = __import__(module_name,globals(),locals())
    else:
        mod = __import__(module_name[:n],globals(),locals())
    # logging.info("{}".format(dir(mod)))
    for attr in dir(mod):
        if attr.startswith('_'):
            # logging.info('{}'.format(attr))
            continue
        fn = getattr(mod,attr)
        # logging.info("-----{}-----".format(fn.__name__))
        if callable(fn):
            try:
                method = getattr(fn,'__method__')
                path = getattr(fn,'__route__')
            except:
                pass
                # logging.info("{} no attr!".format(fn.__name__))
            else:
                logging.info("success get method:{}".format(fn.__name__))
                if method and path:
                    add_route(app,fn)







