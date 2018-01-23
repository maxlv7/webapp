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
        for k,v in zip(names,values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'dict obj has no attr %s'%key)

    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults,override):
    r = dict()

    for k,v in defaults.items():
        if k in override:
            if isinstance(v,dict):
                r[k] = merge(v,override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

def toDict(d):
    D = Dict()
    for k,v in d.items():
        D[k] = toDict(b) if isinstance(v,dict) else v
    return D


# 取得默认配置文件的配置信息
configs = config_default.configs

try:
    import config_override
    configs = merge(configs,config_override.configs)
except ImportError:
    pass

configs = toDict(configs)



