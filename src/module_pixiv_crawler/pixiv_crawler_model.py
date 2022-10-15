from loguru import logger
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Text
from sqlalchemy import SmallInteger
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


# 创建对象的基类:
Base = declarative_base()


# 多对多的关系表定义
IllustTag = Table(
    'illust_tag', Base.metadata,
    Column('tagid', Integer, ForeignKey("tag.tagid"), primary_key=True, nullable=False),
    Column('illustid', Integer, ForeignKey("illust.illustid"), primary_key=True, nullable=False)
)

IllustPixivision = Table(
    'illust_pixivision', Base.metadata,
    Column('aid', Integer, ForeignKey("pixivision.aid"), primary_key=True, nullable=False),
    Column('illustid', Integer, ForeignKey("illust.illustid"), primary_key=True, nullable=False)
)


class User(Base):
    __tablename__ = 'user'

    def __repr__(self):
        return f'User(userid={self.userid}, username="{self.username}")'

    userid = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(64), nullable=False)

    sql_create_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp())
    sql_update_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp(),
                             onupdate=func.current_timestamp())

    illusts = relationship('Illust', viewonly=True)


class Tag(Base):
    __tablename__ = 'tag'

    def __repr__(self):
        return f'Tag(tagid={self.tagid}, tagname="{self.tagname}", tagtransname="{self.tagtransname}")'

    tagid = Column(Integer, primary_key=True, nullable=False)
    tagname = Column(String(128), nullable=False, index=True)
    tagtransname = Column(String(128))

    sql_create_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp())
    sql_update_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp(),
                             onupdate=func.current_timestamp())

    illusts = relationship('Illust', secondary=IllustTag, viewonly=True)


class Pixivision(Base):
    __tablename__ = 'pixivision'

    def __repr__(self):
        return f'Pixivision(' \
               f'aid={self.aid}, title="{self.title}", type="{self.type}", ' \
               f'description="{self.description[:10]}...")'

    aid = Column(Integer, primary_key=True, nullable=False)
    title = Column(String(128), nullable=False)
    type = Column(String(16), nullable=False)
    description = Column(String(1024), nullable=False, default="")

    sql_create_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp())
    sql_update_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp(),
                             onupdate=func.current_timestamp())

    illusts = relationship('Illust', secondary=IllustPixivision, viewonly=True)


class Illust(Base):
    __tablename__ = 'illust'

    def __repr__(self):
        return str({
            'illustid': self.illustid,
            'user': self.user
        })

    illustid = Column(Integer, primary_key=True, nullable=False)
    userid = Column(Integer, ForeignKey("user.userid"), nullable=False, index=True)

    illust_type = Column(SmallInteger, nullable=False, index=True)
    title = Column(String(40), nullable=False)
    nums = Column(SmallInteger, nullable=False, index=True)
    restrict = Column(SmallInteger, nullable=False, index=True)
    description = Column(Text)

    bookmark_cnt = Column(Integer, nullable=False, index=True)
    like_cnt = Column(Integer, nullable=False, index=True)
    comment_cnt = Column(Integer, nullable=False, index=True)
    view_cnt = Column(Integer, nullable=False, index=True)

    create_time = Column(TIMESTAMP, nullable=False)
    upload_time = Column(TIMESTAMP, nullable=False)

    height = Column(Integer, nullable=False, index=True)
    width = Column(Integer, nullable=False, index=True)
    filesize = Column(Integer, nullable=False, index=True)

    sql_create_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp())
    sql_update_time = Column(TIMESTAMP, nullable=False, default=func.current_timestamp(),
                             onupdate=func.current_timestamp())

    user = relationship("User")
    tags = relationship('Tag', secondary=IllustTag)
    pixivisions = relationship('Pixivision', secondary=IllustPixivision)
