from orm import Model, StringField, IntegerField
import asyncio
class User(Model):
    __table__ = 'users'

    id = IntegerField(primary_key=True)
    name = StringField()



# 创建实例:
user = User(id=123, name='Michael')
# 存入数据库:
user.save()
# 查询所有User对象:
# users = User.findAll()