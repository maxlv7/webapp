# 定义Feild基类，负责保存db表的字段名和字段类型

class Field(object):

    def __init__(self,name,column_type,primary_key,default):
        # 表的字段有名字，类型，是否为主键和默认值
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    # 输出表的信息
    def __str__(self):
        # return "<%s, %s: %s>"%(self.__class__.name,self.column_type,self.name)
        return "<%s, %s: %s>"%(self.__class__.__name__,self.column_type,self.name)
    #     # return "222222222"

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)
