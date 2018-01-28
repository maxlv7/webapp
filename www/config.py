import config_default

# 自定义字典
class Dict(dict):
    def __init__(self,names=(),values=(),**kw):
        '''
           initial funcion.
           names: key in dict
           values: value in dict
        '''
        super().__init__(**kw)
        # 建立键值对关系
        for k,v in zip(names,values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'dict obj has no attr %s'%key)

    def __setattr__(self, key, value):
        self[key] = value

    # 创建一个空的字典,用于配置文件的融合,而不对任意配置文件做修改
    # 1) 从默认配置文件取key,优先判断该key是否在自定义配置文件中有定义
    # 2) 若有,则判断value是否是字典,
    # 3) 若是字典,重复步骤1
    # 4) 不是字典的,则优先从自定义配置文件中取值,相当于覆盖默认配置文件
def merge(defaults,override):
    r = {}

    for k,v in defaults.items():
        if k in override:
            if isinstance(v,dict):
                r[k] = merge(v,override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    # 返回混合好的字典
    return r

def toDict(d):
    D = Dict()
    for k,v in d.items():
        D[k] = toDict(v) if isinstance(v,dict) else v
    return D


# 取得默认配置文件的配置信息
configs = config_default.configs

try:
    import config_override
    configs = merge(configs,config_override.configs)
except ImportError:
    pass

configs = toDict(configs)



