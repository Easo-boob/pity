import os
from datetime import datetime

from starlette.background import BackgroundTask
from starlette.responses import FileResponse


class PityResponse(object):

    @staticmethod
    def model_to_dict(obj, *ignore: str):
        if getattr(obj, '__table__', None) is None:
            return obj
        data = dict()
        for c in obj.__table__.columns:
            if c.name in ignore:
                # 如果字段忽略, 则不进行转换
                continue
            val = getattr(obj, c.name)
            if isinstance(val, datetime):
                data[c.name] = val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                data[c.name] = val
        return data

    @staticmethod
    def dict_model_to_dict(obj):
        for k, v in obj.items():
            if isinstance(v, dict):
                PityResponse.dict_model_to_dict(v)
            elif isinstance(v, list):
                obj[k] = PityResponse.model_to_list(v)
            else:
                obj[k] = PityResponse.model_to_dict(v)
        return obj

    @staticmethod
    def json_serialize(obj):
        return {k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v for k, v in dict(obj).items()}

    @staticmethod
    def parse_sql_result(data: list):
        columns = []
        if len(data) > 0:
            columns = list(data[0].keys())
        return columns, [PityResponse.json_serialize(obj) for obj in data]

    @staticmethod
    def model_to_list(data: list, *ignore: str):
        return [PityResponse.model_to_dict(x, *ignore) for x in data]

    @staticmethod
    def success(data=None, code=0, msg="操作成功"):
        return dict(code=code, msg=msg, data=data)

    @staticmethod
    def records(data: list, code=0, msg="操作成功"):
        return dict(code=code, msg=msg, data=PityResponse.model_to_list(data))

    @staticmethod
    def success_with_size(data=None, code=0, msg="操作成功", total=0):
        if data is None:
            return dict(code=code, msg=msg, data=list(), total=0)
        return dict(code=code, msg=msg, data=data, total=total)

    @staticmethod
    def failed(msg, code=110, data=None):
        return dict(code=code, msg=str(msg), data=data)

    @staticmethod
    def file(filepath, filename):
        return FileResponse(filepath, filename=filename, background=BackgroundTask(lambda: os.remove(filepath)))
