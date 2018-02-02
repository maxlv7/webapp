# WebApp

# 演示Demo http://blog.maxlv.org
---

# 项目定位是一个由Python实现的个人博客网站。

---

项目后端使用Python3.63编写，基于aiohttp库，并以Jinja2作为模板引擎。使用MySQL数据库。
前端部分使用的是uikit CSS框架。内含自己实现的简易web框架和ORM框架。

---

**开发日志：**

- 1.9, 搭建开发环境
- 1.10 - 1.14，编写ORM
- 1.16 - 1.19，编写web框架，完成API的设计
- 1.21, 构建前端(基本抄的)
- 1.22, 编写基本api
- 1.24-1.25, 编写用户注册，登陆api
- 1.27-1.28, 编写日志创建管理页
- 基本完成所有功能
- 准备学习flask,用flask做一个可以用的博客，这个博客只做为一个blog

---

# 入口：


后端API包括：

获取日志：GET /api/blogs

创建日志：POST /api/blogs

修改日志：POST /api/blogs/:blog_id

删除日志：POST /api/blogs/:blog_id/delete

获取评论：GET /api/comments

创建评论：POST /api/blogs/:blog_id/comments

删除评论：POST /api/comments/:comment_id/delete

创建新用户：POST /api/users

获取用户：GET /api/users

管理页面包括：

评论列表页：GET /manage/comments

日志列表页：GET /manage/blogs

创建日志页：GET /manage/blogs/create

修改日志页：GET /manage/blogs/

用户列表页：GET /manage/users

用户浏览页面包括：

注册页：GET /register

登录页：GET /signin

注销页：GET /signout

首页：GET /

日志详情页：GET /blog/:blog_id
