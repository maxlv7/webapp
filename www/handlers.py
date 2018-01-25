from web_frame import get,post

from models import User, Comment, Blog, next_id

from apis import *

from aiohttp import web

from config import configs

import time,re,hashlib,json

import logging
logging.basicConfig(level=logging.INFO)

COOKIE_NAME = 'lisession'
_COOKIE_KEY = configs.session.secret




# 通过用户信息计算加密cookie
def user2cookie(user, max_age):
    '''Generate cookie str by user.'''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age)) # expires(失效时间)是当前时间加上cookie最大存活时间的字符串
    # 利用用户id,加密后的密码,失效时间,加上cookie密钥,组合成待加密的原始字符串
    s = "%s-%s-%s-%s" % (user.id, user.passwd, expires, _COOKIE_KEY)
    # 生成加密的字符串,并与用户id,失效时间共同组成cookie
    L = [user.id, expires, hashlib.sha1(s.encode("utf-8")).hexdigest()]
    return "-".join(L)


@get('/')
async def index(request):
    logging.info("调用了index。。。")
    summary = 'test test test'
    blogs = [
        Blog(id='11',name='test',created_at=time.time()-120,summary="123"),
        # Blog(id='21',name='test',created_at=time.time()-7200),
        # Blog(id='21',name='test',created_at=time.time()-120),
        # Blog(id='21',name='test1',created_at=time.time()-120)
        # Blog(id='1', name='test', summary=summary, created_at=1516520805.2515)
        # Blog(id='2', name='test', summary=summary, created_at=time.time()-3600),
        # Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }
# api 查找用户
@get('/api/users')
async def api_get_users():
    users = await User.findAll()
    return dict(users=users)

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

#api 创建用户
@post('/api/users')
async def api_register_user(*,name,email,passwd):
    logging.info("调用了创建用户...")
    if not name or not name.strip():
        raise APIValueError("name")
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError("email")
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError("passwd")

    # 查找数据库里是否存在email
    user = await User.findAll('email=?',[email])

    if len(user) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')

    #数据库里没有email信息，说明是第一次注册
    logging.info("before nextid")
    uid = next_id()
    sha1_passwd = '%s:%s'%(uid,passwd)

    user = User(id=uid,name=name.strip(),email=email,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image="xxx")
    await user.save()

    r = web.Response()
    r.set_cookie(name=COOKIE_NAME,value=user2cookie(user,600),max_age=600,httponly=True)
    logging.info("set cookie...")

    user.passwd = '******'
    logging.info("user.passwd...")

    # 设置content_type,将在data_factory中间件中继续处理
    r.content_type = 'application/json'
    logging.info("content_type...")

    r.body = json.dumps(user,ensure_ascii=False).encode('utf-8')

    logging.info("handlers r ==>%s" % r)
    return r
# -----------------------register-------------------------------------#
@get('/register')
async def register():
    return {
        '__template__':'register.html'
    }
@get('/signin')
async def signin():
    return {
        '__template__':'signin.html'
    }
# ------------------------signin------------------------------------#

@post('/api/authenticate')
def authenticate(*,email,passwd):
    pass





