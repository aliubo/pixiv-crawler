import enum
import datetime
from typing import Generator, NamedTuple, Optional


class ApiMetaArgument(NamedTuple):
    PHPSESSID: str
    PROXY: str


class ArtworkType(enum.Enum):
    ILLUST = 0  # 插画
    MANGA = 1  # 漫画
    UGORIA = 2  # 动图


class ArtworkTag(NamedTuple):
    name: str
    translation: str


class ArtworkRestrict(enum.Enum):
    NON_R18 = 0  # 非R18
    R18 = 1  # R18
    R18G = 2  # R18G


class RankType(enum.Enum):
    DAILY = 'daily'  # 日榜
    WEEKLY = 'weekly'  # 周榜
    MONTHLY = 'monthly'  # 月榜
    NEWBIE = "rookie"  # 新人榜
    ORIGINAL = "original"  # 原创榜
    DAILY_AI = "daily_ai"  # 日榜-ai
    MALE = "male"  # 男性喜爱
    FEMALE = "female"  # 女性喜爱

    DAILY_R18 = 'daily_r18'
    WEEKLY_R18 = 'weekly_r18'
    WEEKLY_R18G = 'r18g'
    DAILY_AI_R18 = "daily_r18_ai"
    MALE_R18 = "male_r18"
    FEMALE_R18 = "female_r18"


class ArtworkInfo(object):
    artwork_id: int
    user_id: int
    user_name: str
    artwork_type: ArtworkType
    tags: list[ArtworkTag]
    image_download_urls: list[str]
    title: str
    nums: int
    restrict: ArtworkRestrict
    desc: str
    bookmark_cnt: int
    like_cnt: int
    comment_cnt: int
    view_cnt: int
    create_time: datetime.datetime
    upload_time: datetime.datetime
    height: int
    width: int


class PixivisionInfo(NamedTuple):
    aid: int
    title: str
    desc: str
    pixivision_type: str
    artworks: list[ArtworkInfo]


class ArtworkOptions(object):
    def __init__(self) -> None:
        """
        update: bool, 是否更新已存在的artwork
        only_r18: bool, 是否只爬取R18
        only_non_r18: bool, 是否只爬取非R18
        skip_manga: bool, 是否跳过漫画
        artwork_types: list[ArtworkType], 只爬取指定类型的artwork
        """
        self.update = False
        self.only_r18 = False
        self.only_non_r18 = False
        self.skip_manga = True
        self.artwork_types: list[ArtworkType] | None = None

    def valid_by_artwork_info(self, artwork_info: ArtworkInfo) -> Optional[str]:
        if self.only_r18 and artwork_info.restrict == ArtworkRestrict.NON_R18:
            return "only_r18"
        if self.only_non_r18 and artwork_info.restrict != ArtworkRestrict.NON_R18:
            return "only_non_r18"
        if self.skip_manga and artwork_info.artwork_type == ArtworkType.MANGA:
            return "skip_manga"
        if self.artwork_types and artwork_info.artwork_type not in self.artwork_types:
            return "artwork_types"


class PixivApi(object):
    def get_image(self, url: str) -> bytes:
        raise NotImplementedError

    def get_artwork_info(self, artwork_id: int, options: ArtworkOptions) -> ArtworkInfo:
        # 获取某个插画的详细信息
        raise NotImplementedError

    def get_artworks_by_userid(self, user_id: int, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 根据用户id获取所有插画作品
        raise NotImplementedError

    def get_artworks_by_bookmark_new(self, page: int, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 获取关注的用户最新的插画作品
        raise NotImplementedError

    def get_artworks_by_pixivision_aid(self, aid: int, options: ArtworkOptions) -> PixivisionInfo:
        # 获取pixivision的插画作品，根据aid
        raise NotImplementedError

    def get_artworks_by_recommend(self, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 获取推荐的插画作品(首页的推荐作品)
        raise NotImplementedError

    def get_artworks_by_rank(self, rank_type: RankType, date: int, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 根据排行榜获取插画作品
        # date: 8位数字，如20220101
        raise NotImplementedError

    def get_artworks_by_request_recommend(self, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 获取推荐的接稿的插画作品(接稿页面的推荐作品)
        raise NotImplementedError

    def get_userids_by_request_creator(self, options: ArtworkOptions) -> list[int]:
        # 获取推荐的接稿的用户id
        raise NotImplementedError

    def get_userids_by_similar_user(self, user_id: int, options: ArtworkOptions) -> list[int]:
        # 获取相似用户的用户id(当关注一个用户时，pixiv给的推荐用户)
        raise NotImplementedError

    def get_artworks_by_user_bookmark(self, user_id: int, page: int, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 获取用户的收藏作品
        raise NotImplementedError

    def get_artworks_by_tag_popular(self, tag_name: str, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 从指定tag获取热门作品
        raise NotImplementedError

    def get_userids_by_recommend(self, options: ArtworkOptions) -> list[int]:
        # 获取推荐的用户id（首页展示的）
        raise NotImplementedError

    def get_artworks_by_similar_artwork(self, artwork_id: int, options: ArtworkOptions) -> list[ArtworkInfo]:
        # 获取相似作品（作品底部展示的，以及收藏时浮出的）
        raise NotImplementedError


def new_pixiv_api(meta: ApiMetaArgument) -> PixivApi:
    from . import api
    return api.PixivApiImpl(meta)


def origin_url_2_all_url(origin_url: str, nums: int) -> Generator[str, None, None]:
    template_url: str = '_p{}.'.join(origin_url.split('_p0.'))
    return (
        template_url.format(i)
        for i in range(nums)
    )


def new_filter(**kwargs) -> ArtworkOptions:
    options = ArtworkOptions()
    for k, v in kwargs.items():
        setattr(options, k, v)
    return options
