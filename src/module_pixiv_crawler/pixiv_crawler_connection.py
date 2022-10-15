from loguru import logger
from datetime import datetime

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from utils.webrequest_factory import WebRequestFactory
from utils.fileio_factory import FileIOFactory
from .pixiv_crawler_service import Service
from .pixiv_crawler_utils import ThumbnailLevelEnum

__all__ = 'connect'


def connect(sql_url, file_path, session_id, proxy_host, timezone = 'UTC') -> Service:
    """
    建立一个关于Pixiv网站的服务，需要提供必要的初始信息

    :param sql_url: 用于连接数据库的url连接，格式参考 https://docs.sqlalchemy.org/en/14/core/engines.html
    :param file_path: 用于存储文件的根路径，需指向一个目录
    :param session_id: 登录pixiv后，获取到的PHPSESSION的cookies值
    :param proxy_host:
    :param timezone:
    :return: 返回一个Server类
    """

    # generate FileIO
    file = FileIOFactory()
    file.setRootPath(file_path)
    file.setDirectoryTree({
        "img_origin": None,
        # 为ThumbnailLevelEnum每一个成员建立一个文件夹
        "img_thumbnail": {i.name: None for i in ThumbnailLevelEnum}
    })
    file = file.generate()

    # generate WebRequest
    web = WebRequestFactory()
    web.addHeaders({
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, "
                      "like Gecko) Chrome/81.0.4044.138 Safari/537.36",
        "referer": "https://www.pixiv.net/",
        "accept-language": "en,zh-CN;q=0.9,zh;q=0.8"
    })
    web.addProxy(proxy_host)
    web.addCookies({
        "login_ever": "yes",
        "user_lang": "zh"
    })
    web.addCookie("PHPSESSID", session_id)
    web = web.generate()

    # 如果表不存在，使用指定的sql引擎自动建表
    from .pixiv_crawler_model import Base
    sql_engine = None

    try:
        sql_engine = create_engine(sql_url)  # 创建引擎
    except Exception as msg:
        logger.error(f"创建引擎失败，sql: {sql_url}, msg: {msg}")

    try:
        Base.metadata.create_all(sql_engine)  # 建表
    except Exception as msg:
        logger.error(f"自动化建表失败，msg: {msg}")

    # 以计算机本地时区连接
    sql_sessionmaker = sessionmaker(sql_engine)  # session生成器包装引擎
    logger.info(f"当前设置的时区为 {timezone}")

    def _sql():
        session = sql_sessionmaker()
        # print(session.query(func.current_timestamp()).all())
        # session.execute(f"SET TIME ZONE '{timezone}'")
        return session

    sql = _sql

    # 为了降低耦合性，生成三个基本的对象给Service传递
    # connection不接触本包里的其他模块，只调用包里的service模块
    return Service(file, web, sql, timezone)
