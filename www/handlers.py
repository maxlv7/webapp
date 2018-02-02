from web_frame import get,post

from models import User, Comment, Blog, next_id

from apis import *

from aiohttp import web

from config import configs

import time,re,hashlib,json,markdown2


import logging
logging.basicConfig(level=logging.INFO)

COOKIE_NAME = 'lisession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

#---------------cookie和认证--------------------------------------#

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

# 解密cookie
async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid,expires,sha1 = L

        if int(expires)<time.time():
            return None
        user = await User.find(uid)

        if user is None:
            return None
        # 利用用户id,加密后的密码,失效时间,加上cookie密钥,组合成待加密的原始字符串
        # 再对其进行加密,与从cookie分解得到的sha1进行比较.若相等,则该cookie合法
        s = "%s-%s-%s-%s"%(uid,user.passwd,expires,_COOKIE_KEY)

        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info("invalid sha1")
            return None
        user.passwd = "******"
        return user
    except Exception as e:
        logging.exception(e)
    return None

#检察是是否管理员
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def get_page_index(page_str):
    # 将传入的字符串转为页码信息, 实际只是对传入的字符串做了合法性检查
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

#文本转html
def text2html(text):
    # 先用filter函数对输入的文本进行过滤处理: 断行,去首尾空白字符
    # 再用map函数对特殊符号进行转换,在将字符串装入html的<p>标签中
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    # lines是一个字符串列表,将其组装成一个字符串,该字符串即表示html的段落
    return ''.join(lines)

# 用户登陆验证
@post('/api/authenticate')
async def authenticate(*,email,passwd):
    logging.info("authenticate被调用...")
    if not email:
        raise APIValueError("email","Invalid email")

    if not passwd:
        raise APIValueError("passwd","Invalid passwd")

    users = await User.findAll('email=?',[email])
    if len(users) == 0:
        raise APIValueError("email","email not exits")
    user = users[0]

    #验证密码
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b":")
    sha1.update(passwd.encode('utf-8'))

    if user.passwd != sha1.hexdigest():
        raise APIValueError("passwd","Invalid password")

    # 用户登录之后,同样的设置一个cookie,与注册用户部分的代码完全一样

    r = web.Response()
    r.set_cookie(name=COOKIE_NAME, value=user2cookie(user, 600), max_age=600, httponly=True)
    logging.info("set cookie...")

    user.passwd = '******'
    logging.info("user.passwd...")

    # 设置content_type,将在data_factory中间件中继续处理
    r.content_type = 'application/json'
    logging.info("content_type...")

    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')

    logging.info("handlers r ==>%s" % r)
    return r

#---------------cookie和认证--------------------------------------#

#---------------------------后端API--------------------------------------------#

#获取单条日志
@get('/api/blogs/{id}')
async def api_get_blog(*,id):
    blog = await Blog.find(id)
    return blog

#获取所有日志
@get('/api/blogs')
async def api_blogs(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)') #num为总数

    p = Page(num,page_index)

    if num == 0:
        return dict(page=p,blogs=())

    # blogs = await Blog.findAll(orderBy="create_at desc",limit=(p.offset, p.limit))
    blogs = await Blog.findAll()

    return dict(page=p,blogs=blogs)

# 创建日志
# 从js的postJSON函数接受表单信息
@post('/api/blogs')
async def api_create_blog(request,*,name,summary,content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError("name", "name cannot be empty")
    if not summary or not summary.strip():
        raise APIValueError("summary", "summary cannot be empty")
    if not content or not content.strip():
        raise APIValueError("content", "content cannot be empty")

    blog = Blog(user_id = request.__user__.id,user_name=request.__user__.name,user_image=request.__user__.image,name=name.strip(),summary=summary.strip(),content=content.strip())
    await blog.save()

    return blog

#修改日志
@post('/api/blogs/{id}')
async def modify_blog(id,request,*,name,summary,content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError("name", "name cannot be empty")
    if not summary or not summary.strip():
        raise APIValueError("summary", "summary cannot be empty")
    if not content or not content.strip():
        raise APIValueError("content", "content cannot be empty")
    blog = await Blog.find(id)

    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog

# 删除日志
@post('/api/blogs/{id}/delete')
async def api_delete_blog(request,*,id):
    check_admin(request)

    blog = await Blog.find(id)

    await blog.remove()
    # logging.info("id = {}".format(id))
    return dict(id=id)


#创建用户
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

    user = User(id=uid,name=name.strip(),email=email,passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image="https://i.loli.net/2018/01/31/5a716bbd99180.jpg")
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

#获取用户
@get('/api/users')
async def api_get_users():
    users = await User.findAll()
    # print(users)
    # for u in users:
    #     u['id'] = 2
    return dict(users=users)

#---------------------------后端API--------------------------------------------#

#---------------------------管理页面--------------------------------------------#

#管理重定向
@get('/manage/')
def manage():
    return "redirect:/manage/blogs"

#日志列表页
@get('/manage/blogs')
def manange_blogs(*,page='1'):
    return {
        '__template__':'manage_blogs.html',
        'page_index':get_page_index(page)
    }

#创建日志页
@get('/manage/blogs/create')
def manage_create_blog():
    return{
        '__template__':'manage_blog_edit.html',
        'id':'',
        'action':'/api/blogs'
    }

#修改日志页
@get('/manage/blogs/edit/{id}')
def manage_edit_blog(*,id):
    return {
        '__template__':'manage_blog_edit.html',
        'id':id,
        'action':'/api/blogs/%s'%id
    }

#评论列表页
@get('/manage/comments')
def manage_comments(*,page='1'):
    return {
        '__template__':'manage_comments.html',
        "page_index":get_page_index(page)
    }

#用户列表页
@get('/manage/users')
def manage_users(*,page='1'):
    return {
        '__template__':'manage_users.html',
        'page_index':get_page_index(page)
    }




#---------------------------管理页面--------------------------------------------#

#---------------------------用户浏览页面--------------------------------------------#

#注册
@get('/register')
async def register():
    return {
        '__template__':'register.html'
    }

#登陆
@get('/signin')
async def signin():
    return {
        '__template__':'signin.html'
    }

#登出
@get('/signout')
def signout(request):
    referer = request.headers.get("Referer")
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME,"-deleted-",max_age=0,httponly=True)
    logging.info("user sign out。。。")
    return r

#日志详情页
@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)

    comments = await Comment.findAll('blog_id=?',[id],orderBy='created_at desc')

    for c in comments:
        c.html_content = text2html(c.content)

    blog.html_content = markdown2.markdown(blog.content)

    return {
        '__template__':'blog.html',
        'blog':blog,
        "comments":comments
    }

#首页
@get('/')
async def index(*,page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num)

    if num ==0:
        blogs = []
    else:
        blogs = await Blog.findAll()
    logging.info("调用了index。。。")

    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
        'page':page
    }

#---------------------------用户浏览页面--------------------------------------------#










