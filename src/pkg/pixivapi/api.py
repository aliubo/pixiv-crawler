import pkg.pixivapi as pixivapi
import requests
import parsel
import datetime
import typing
import functools


BASE_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, "
                  "like Gecko) Chrome/81.0.4044.138 Safari/537.36",
    "accept-language": "en,zh-CN;q=0.9,zh;q=0.8",
    "referer": "https://www.pixiv.net/",
}


LazyResponse = typing.Callable[[], requests.Response]


class ArtworkInfoImpl(pixivapi.ArtworkInfo):
    def __init__(self, res: LazyResponse | requests.Response) -> None:
        self._raw_resp: LazyResponse | requests.Response = res
        self._resp_json: dict = {}
        self._timezone = datetime.datetime.now().astimezone().tzinfo.tzname(None)

    def _get_body(self) -> dict:
        if self._resp_json:
            return self._resp_json['body']
        if callable(self._raw_resp):
            self._raw_resp = self._raw_resp()._raw_resp
        if isinstance(self._raw_resp, requests.Response):
            self._resp_json = self._raw_resp.json()
        return self._resp_json['body']

    @property
    def artwork_id(self) -> int:
        body = self._get_body()
        return int(body['illustId'])

    @property
    def user_id(self) -> int:
        body = self._get_body()
        return int(body['userId'])

    @property
    def user_name(self) -> str:
        body = self._get_body()
        return body['userName']

    @property
    def artwork_type(self) -> pixivapi.ArtworkType:
        body = self._get_body()
        return pixivapi.ArtworkType(
            int(body['illustType'])
        )

    @property
    def tags(self) -> list[pixivapi.ArtworkTag]:
        body = self._get_body()
        tags: list[pixivapi.ArtworkTag] = []

        used_tag = set()
        for tag_info in body['tags']['tags']:
            tag = tag_info['tag']
            translation = tag_info.get('translation', {})

            tag_trans = translation.get('en', '') if translation else ''

            if tag in used_tag:  # 网站部分返回的会出现重复tag的问题（e.g. 69353795）
                continue
            used_tag.add(tag)
            tags.append(pixivapi.ArtworkTag(name=tag, translation=tag_trans))

        return tags

    @property
    def image_download_urls(self) -> list[str]:
        if self.artwork_type == pixivapi.ArtworkType.UGORIA:
            return []

        body = self._get_body()
        original_url = body['urls']['original']
        return pixivapi.origin_url_2_all_url(original_url, self.nums)

    @property
    def title(self) -> str:
        body = self._get_body()
        return body['title']

    @property
    def nums(self) -> int:
        body = self._get_body()
        return int(body['pageCount'])

    @property
    def restrict(self) -> pixivapi.ArtworkRestrict:
        body = self._get_body()
        return pixivapi.ArtworkRestrict(
            int(body['xRestrict'])
        )

    @property
    def desc(self) -> str:
        body = self._get_body()
        return body['description']

    @property
    def bookmark_cnt(self) -> int:
        body = self._get_body()
        return body['bookmarkCount']

    @property
    def like_cnt(self) -> int:
        body = self._get_body()
        return body['likeCount']

    @property
    def comment_cnt(self) -> int:
        body = self._get_body()
        return body['commentCount']

    @property
    def view_cnt(self) -> int:
        body = self._get_body()
        return body['viewCount']

    @property
    def create_time(self) -> datetime.datetime:
        body = self._get_body()
        tm = datetime.datetime.fromisoformat(body['createDate'])
        return tm.astimezone(None)

    @property
    def upload_time(self) -> datetime.datetime:
        body = self._get_body()
        tm = datetime.datetime.fromisoformat(body['uploadDate'])
        return tm.astimezone(None)

    @property
    def height(self) -> int:
        body = self._get_body()
        return body['height']

    @property
    def width(self) -> int:
        body = self._get_body()
        return body['width']


class PixivApiImpl(pixivapi.PixivApi):
    def __init__(self, meta: pixivapi.ApiMetaArgument):
        self._meta = meta
        self._session = requests.session()
        self._init_session()

    def _init_session(self):
        if self._meta.PROXY:
            self._session.proxies.update({
                "http": self._meta.PROXY,
                "https": self._meta.PROXY
            })
        if self._meta.PHPSESSID:
            self._session.cookies.update({
                "PHPSESSID": self._meta.PHPSESSID
            })

    def get_artwork_info(self, artwork_id: int, options: pixivapi.ArtworkOptions) -> pixivapi.ArtworkInfo:
        url = f"https://www.pixiv.net/ajax/illust/{artwork_id}?lang=zh"
        res = self._session.get(url=url, headers=BASE_HEADERS)
        return ArtworkInfoImpl(res)

    def get_artworks_by_userid(self, user_id: int, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = f"https://www.pixiv.net/ajax/user/{user_id}/profile/all?lang=zh"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        artworks = res['body']['illusts']
        artworks = [int(i) for i in artworks]
        return [
            ArtworkInfoImpl(functools.partial(self.get_artwork_info, artwork_id=i))
            for i in artworks
        ]

    def get_artworks_by_bookmark_new(self, page: int, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = f"https://www.pixiv.net/ajax/bookmark_new_illust.php?p={page}&rest=show"
        if options.only_r18:
            url += "&mode=r18"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in res['body']['page']['ids']
        ]

    def get_artworks_by_pixivision_aid(self, aid: int, options: pixivapi.ArtworkOptions) -> pixivapi.PixivisionInfo:
        url = f"https://www.pixivision.net/zh/a/{aid}"
        res = self._session.get(url=url, headers=BASE_HEADERS).text

        parsel_obj = parsel.Selector(res)
        title = parsel_obj.css('.am__title')[0].root.text
        a_type = parsel_obj.css('.am__categoty-pr').css('a').attrib['data-gtm-label']
        description = parsel_obj.css('.am__description')[0].root.text_content()

        if a_type != 'illustration':
            return pixivapi.PixivisionInfo(aid, title, description, a_type,[])

        artwork_ids = tuple(
            int(i.css('a').attrib['href'].split('/')[-1])
            for i in parsel_obj.css('.am__body')[0].css('.am__work__main')
        )

        res = pixivapi.PixivisionInfo(
            aid, title, description, a_type, [
                functools.partial(self.get_artwork_info, artwork_id=i)
                for i in artwork_ids
            ]
        )
        return res

    def get_image(self, url: str) -> bytes:
        res = self._session.get(url=url, headers=BASE_HEADERS)
        res.raise_for_status()
        return res.content

    def get_artworks_by_recommend(self, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = "https://www.pixiv.net/ajax/top/illust?lang=zh"
        url += "&mode=r18" if options.only_r18 else "&mode=all"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        artworks = res['body']['page']['recommend']['ids']
        artworks = list(set((int(i) for i in artworks)))
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in artworks
        ]

    def get_artworks_by_rank(self, rank_type: pixivapi.RankType, date: int, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = f"https://www.pixiv.net/ranking.php?&content=illust&p=1&format=json&date={date}"
        url += f"&mode={rank_type.value}"
        res = self._session.get(url=url, headers=BASE_HEADERS).text

        parsel_obj = parsel.Selector(res)
        artwork_ids = [i.attrib['data-id'] for i in parsel_obj.css('.ranking-items')[0].css('section')]
        artwork_ids = list(set((int(i) for i in artwork_ids)))
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in artwork_ids
        ]

    def get_artworks_by_request_recommend(self, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = f"https://www.pixiv.net/ajax/commission/page/request/complete/illust?p=1&lang=zh"
        if options.only_r18:
            url += "&mode=r18"
        elif options.only_non_r18:
            url += "&mode=safe"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        reqs = res['body']['requests']
        artworks = [int(req['postWork']['postWorkId']) for req in reqs]
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in artworks
        ]

    def get_userids_by_request_creator(self, options: pixivapi.ArtworkOptions) -> list[int]:
        url = f"https://www.pixiv.net/ajax/commission/page/request/creators/illust/ids?&follows=0&p=1&lang=zh"
        if options.only_r18:
            url += "&mode=r18"
        elif options.only_non_r18:
            url += "&mode=safe"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        userids = res['body']['page']['creatorUserIds']
        userids = list(set([int(creater) for creater in userids]))
        return userids

    def get_userids_by_similar_user(self, user_id: int, options: pixivapi.ArtworkOptions) -> list[int]:
        url = f"https://www.pixiv.net/ajax/user/{user_id}/recommends?userNum=20&workNum=3&lang=zh"
        url += "&isR18=false" if options.only_non_r18 else "&isR18=true"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        userids = [int(i['userId']) for i in res['body']['recommendUsers']]
        userids = list(set(userids))
        return userids

    def get_artworks_by_user_bookmark(self, user_id: int, page: int, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = f"https://www.pixiv.net/ajax/user/{user_id}/illusts/bookmarks?tag=&offset={page*48}&limit=48&rest=show&lang=zh"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        artworks = [int(i['id']) for i in res['body']['works']]
        artworks = list(set(artworks))
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in artworks
        ]

    def get_artworks_by_tag_popular(self, tag_name: str, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        tag_name = requests.utils.quote(tag_name)
        url = f"https://www.pixiv.net/ajax/search/top/{tag_name}?lang=zh"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        populars = res['body']['popular']
        artworks = populars['permanent'] + populars['recent']
        artwork_ids = [int(i["id"]) for i in artworks]
        artwork_ids = list(set(artwork_ids))
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in artwork_ids
        ]

    def get_userids_by_recommend(self, options: pixivapi.ArtworkOptions) -> list[int]:
        url = "https://www.pixiv.net/ajax/top/illust?mode=all&lang=zh"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        userids = [int(i['userId']) for i in res['body']['users']]
        userids = list(set(userids))
        return userids

    def get_artworks_by_similar_artwork(self, artwork_id: int, options: pixivapi.ArtworkOptions) -> list[pixivapi.ArtworkInfo]:
        url = f"https://www.pixiv.net/ajax/illust/{artwork_id}/recommend/init?limit=20&lang=zh"
        res = self._session.get(url=url, headers=BASE_HEADERS).json()
        artworks = [int(i['id']) for i in res['body']['illusts']]
        artworks = list(set(artworks))
        return [
            functools.partial(self.get_artwork_info, artwork_id=i)
            for i in artworks
        ]
