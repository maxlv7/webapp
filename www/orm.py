import asyncio
import logging
import aiomysql
from fields import Field

#设置调试级别level,此处为logging.INFO,不设置logging.info()没有任何作用等同于pass
logging.basicConfig(level=logging.INFO)

def log(sql,args=()):
    logging.info("ORM==>SQL:%s"%sql)

# 创建一个全局连接池
async def create_pool(loop,**kw):
    logging.info("创建数据库连接池...")
    global _pool
    _pool = await aiomysql.create_pool(
        host = kw.get("host","localhost"),
        port = kw.get("port",3306),
        user = kw["user"],
        password = kw["password"],
        db = kw["db"],
        charset = kw.get("charset","utf8"),
        autocommit = kw.get("autocommit",True),
        maxsize = kw.get("maxsize",10),
        minsize = kw.get("minsize",1),
        loop = loop

    )
#定义一个select函数
async def select(sql,args,size=None):
    log(sql,args)
    global _pool

    # 得到一个连接对象，conn指向这个连接对象
    async with _pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            #sql的占位符是？，mysql是%s
            #excute 代表执行的sql语句
            await cur.execute(sql.replace('?',"%s"),args or ())
        if size:
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()

    # await cur.close()
    logging.info("rows returned:%s"%len(rs))

    return rs

#定义一个通用的exectue函数，用来执行insert,update,delete
async def execute(sql, args, autocommit=True):
    log(sql, args)
    with await _pool as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with await conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', "%s"), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise e
        return affected

# 创建占位符，用于insert，updae，delete语句
def create_args_string(num):
    L = []
    for i in range(num):
        L.append('?')
    return ','.join(L)


# 通过metaclass将子类的映射关系读出来
class ModelMetaclass(type):

    def __new__(cls,name,bases,attrs):
        #排除Model本身
        if name == "Model":
            return type.__new__(cls,name,bases,attrs)

        #获取table名称
        tableName = attrs.get("__table__") or name
        logging.info("Fount model: %s (table: %s)"%(name,tableName))

        #获取所有的Field和主键名
        # 保存当前类属性名和Field字段的映射关系
        mappings = dict()

        # 保存除主键外的属性名
        fields = []
        primaryKey = None

        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info('found mapping: %s ==> %s' % (k, v))
                mappings[k] = v

                # 若字段primary_key为True
                if v.primary_key:

                    #找到主键
                    # 判断主键是否已被赋值
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)

                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError("Primary key not found...")

        # 删除类中的属性，因为会和生成的实例属性重名
        for k in mappings.keys():
            attrs.pop(k)

        escaped_fields = list(map(lambda f: '`%s`' % f, fields))

        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名

        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
        tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
        tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


# orm映射的基类
class Model(dict,metaclass=ModelMetaclass):

    def __init__(self,**kw):
        super().__init__(**kw)

    #设置属性
    def __setattr__(self, key, value):
        self[key] = value

    #得到属性
    def __getattr__(self, key):

        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"Model has no attr named:%s")
    #调用得到值的API
    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value = getattr(self,key,None)

        if value is None:
            filed = self.__mappings__[key]
            if filed is not None:
                value = filed.default() if callable(filed.default) else filed.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self,key,value)
        return value

    @classmethod
    async def find(cls,pk):
        'find object by primary key'
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)

        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]  # 取得主键作为参数
        rows = await execute(self.__delete__, args)  # 调用默认的delete语句
        if rows != 1:
            logging.warn("failed to remove by primary key: affected rows %s" % rows)

    async def update(self):
        # 像time.time,next_id之类的函数在插入的时候已经调用过了,没有其他需要实时更新的值,因此调用getValue
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn("failed to update by primary key: affected rows %s" % rows)










