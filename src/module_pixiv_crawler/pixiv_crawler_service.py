from loguru import logger
from datetime import datetime
from zoneinfo import ZoneInfo
import parsel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select, update, delete, insert, desc
from sqlalchemy import func
from utils.fileio_factory import FileIO
from utils.webrequest_factory import WebRequest
from .pixiv_crawler_model import Illust, Pixivision, User, Tag


class Service(object):
    __slots__ = ('_file', '_web', '_sql', '_tz')

    def __init__(self, file: FileIO, web: WebRequest, sql, timezone = 'UTC'):
        """
        :param file: FileIO对象，使用utils.fileio_factory模块生成
        :param web: WebRequest对象，使用utils.webrequest_factory模块生成
        :param sql: 使用sqlalchemy模块下的sessionmaker(create_engine(url))生成
        """
        if not isinstance(file, FileIO) or not isinstance(web, WebRequest):
            logger.error(f"传递了错误类型的参数, file: {file}, web: {web}, sql: {sql}")
            raise ValueError("传递了错误类型的参数, 参见类构造方法传参解释")

        self._file = file
        self._web = web
        self._sql = sql
        self._tz = timezone

        logger.info("module_pixiv_crawler.Service构造完成")

    def __del__(self):
        del self._sql
        del self._web
        del self._file

    def _call_api_get_json(self, url, method='get', data=None, json=None):
        """
        调用一个pixiv站的api，获取其json数据内容

        :param url: url链接
        :return: json数据
        """
        try:
            content = None
            if method == 'get':
                content = self._web.get(url)
            elif method == 'post':
                content = self._web.post(url, json=json, data=data)
            content = content.json()
            return content
        except Exception as msg:
            logger.error(f"api调用失败，url: {url}, method: {method}, data: {data}, json: {json}, msg: {msg}")
            raise RuntimeError(f"api调用失败，url: {url}，详见日志")

    def download_by_illustid(self, illustid: int) -> bool:
        """
        爬取指定illustid的插画，不支持动图
        如果已存至数据库且硬盘上图片均已下载（使用文件是否存在进行判定），则返回False表示不进行爬取
        或者如果该illust为动图的话(illust_type==2)也返回False表示跳过不爬取
        否则爬取api且重新下载指定illustid的所有图片进行覆盖至硬盘上，并重写指定数据库的该条记录

        :return: 返回指定illustid的图片是否进行了爬取操作
        """
        logger.info(f"调用了 download_by_illustid({illustid})")

        # 0. 仅此方法使用的常量池
        # 跳过的illust_type类型，属于此类型的illust将只记录数据库，不保存图片
        SKIP_ILLUST_TYPE = (2, )

        # 0. 参数检查
        if not isinstance(illustid, int) or illustid < 20:
            raise ValueError("参数illustid应为正整数")

        # 1. 判断是否已保存，如果已存至数据库且硬盘上图片均已下载（使用文件是否存在进行判定），则返回False表示不进行爬取
        with self._sql() as session:
            session: Session
            ans = session.query(Illust).where(Illust.illustid == illustid).one_or_none()
            if ans is not None:
                # 判断illust_type是否需要跳过，如果是直接返回False
                if ans.illust_type in SKIP_ILLUST_TYPE:
                    logger.info(f"illustid:{illustid}的图片类型需跳过(illust_type={ans.illust_type})，之前已存过数据库")
                    return False

                # 判断硬盘上是否缺图片
                all_download = all(
                    self._file.is_exist(f'img_origin/{illustid}_{idx}.jpg')
                    for idx in range(ans.nums)
                )
                if all_download:
                    # 已保存不需要下载
                    logger.info(f"illustid:{illustid} 所有图片已全存至硬盘上且数据库有记录，故略过请求api和下载图片步骤")
                    return False
                else:
                    session.delete(Illust).where(Illust.illustid == illustid)

        # 2. 调用api，获取illust信息
        try:
            api_url = f"https://www.pixiv.net/ajax/illust/{illustid}"
            illust_info = self._call_api_get_json(api_url)['body']
            # BugFix 1: 修复了传来的数据类型不唯一导致运行异常的bug，有小概率页面是str类型，例如illust=47529516
            illust_info['userId'] = int(illust_info['userId'])
            illust_info['id'] = int(illust_info['id'])
            illust_info['illustId'] = int(illust_info['illustId'])
        except Exception as msg:
            raise RuntimeError(f"api获取失败, {msg}")

        # ?3. 如果illust_type需要跳过，单独记录并
        #if illust_info['illustType'] in SKIP_ILLUST_TYPE:
        #    logger.info(f"illustid:{illustid}的图片为动图，跳过")
        #    return False

        # 4. 建立user对象
        user = User(userid=illust_info['userId'], username=illust_info['userName'])

        # 5. 建立tags对象
        tags = []
        with self._sql() as session:
            session: Session
            used_tag = set()
            # 对每一个标签进行检索
            for i in illust_info['tags']['tags']:
                # 如果tag名称重复出现，则跳过
                # 这段特殊检查来自于illustid=69353795有两个相同tag，导致数据库重复插入报错
                if i['tag'] in used_tag:
                    continue
                used_tag.add(i['tag'])
                # 获取tag信息
                tag = session.query(Tag).where(Tag.tagname == i['tag']).one_or_none()
                if tag is None:
                    # 获取最大ID编号
                    maxid = session.query(Tag).order_by(desc(Tag.tagid)).limit(1).one_or_none()
                    if maxid is None:  # 需要特判一下是否是空表
                        maxid = 0
                    else:
                        maxid = maxid.tagid
                    # 创建Tag对象
                    tag = Tag(tagid=maxid + 1, tagname=i['tag'])
                    if i.get('translation', None) is not None:
                        tag.tagtransname = i['translation']['en']
                    # 插入到数据库中
                    session.add(tag)
                tags.append(tag)
            session.commit()

        # 6. 开始逐一下载至硬盘并记录大小，如果是跳过类型则跳过
        if illust_info['illustType'] not in SKIP_ILLUST_TYPE:
            filesize = 0  # 统计所有图片总和大小
            dl_url_base: str = illust_info['urls']['original']
            dl_url_strip = dl_url_base.split('_p0.')
            dl_url_base: str = dl_url_strip[0] + '_p{}.' + dl_url_strip[1]
            for idx in range(illust_info['pageCount']):
                img_url = dl_url_base.format(idx)
                try:
                    img = self._web.get(img_url).bytes()  # 获得图片
                except Exception as msg:
                    logger.error(
                        f"图片下载失败，illustid: {illustid}, idx:{idx}, url: {img_url}, "
                        f"illustInfo: {illust_info}, msg: {msg}"
                    )
                    raise RuntimeError("图片下载失败, 详见日志")

                filename = f"img_origin/{illustid}_{idx}.jpg"  # 文件名
                self._file.open_overwrite_bytes(filename, img)  # 存储在硬盘上
                filesize += len(img)  # 统计所有图片总和大小
        else:
            logger.info(f"illustid:{illustid}的图片类型需跳过(illust_type={illust_info['illustType']}), 仅添加至数据库中实际不下载图片")
            filesize = 0

        # 7. 建立illust对象
        illust = Illust(
            illustid=illustid,  # illustid在参数上
            userid=illust_info['userId'],  # illust_info在第2步骤
            illust_type=illust_info['illustType'],
            title=illust_info['title'],
            nums=illust_info['pageCount'],
            restrict=illust_info['xRestrict'],
            description=illust_info['description'],
            bookmark_cnt=illust_info['bookmarkCount'],
            like_cnt=illust_info['likeCount'],
            comment_cnt=illust_info['commentCount'],
            view_cnt=illust_info['viewCount'],
            create_time=datetime.fromisoformat(illust_info['createDate']).astimezone(ZoneInfo(self._tz)),
            upload_time=datetime.fromisoformat(illust_info['uploadDate']).astimezone(ZoneInfo(self._tz)),
            height=illust_info['height'],
            width=illust_info['width'],
            filesize=filesize,  # filesize在第6步骤
            tags=tags  # tags在第5步骤
        )

        # 8. 存入数据库
        with self._sql() as session:
            # 插入user，判重
            if session.query(User).where(User.userid == user.userid).one_or_none() is None:
                session.add(user)
            # 插入illust，顺带ORM插入illust_tag
            session.add(illust)

            session.commit()

        return True

    def download_by_userid(self, userid: int) -> int:
        """
        爬取指定user的所有插画作品，自动跳过动图

        :return: 返回新增的插画数量
        """
        logger.info(f"调用了 download_by_userid({userid})")

        # 0. 参数检查
        if not isinstance(userid, int) or userid < 10:
            raise ValueError("参数userid应为正整数")

        # 1. 请求API获取user的所有illust数据
        try:
            api_url = f'https://www.pixiv.net/ajax/user/{userid}/profile/all?lang=zh'
            user_info = self._call_api_get_json(api_url)['body']['illusts']
        except Exception as msg:
            raise RuntimeError(f"api获取失败，msg: {msg}")
        user_info = [int(i) for i in user_info]
        user_info.sort()

        # 2. 开始逐一请求下载对应的illustid，统计下载数量
        download_cnt = 0
        for i in user_info:
            if self.download_by_illustid(i):
                download_cnt += 1

        return download_cnt

    def download_by_bookmark_new(self, page):
        """
        爬取用户已关注画师的最新作品，指定页数去爬取

        :param page: 大于等于1的整数
        :return: 返回新增的插画数量
        """
        logger.info(f"调用了 download_by_bookmark_new({page})")

        # 0. 参数检查
        if not isinstance(page, int) or page < 1:
            raise ValueError("参数page错误")

        # 1. api获取该页信息
        try:
            web_url = f'https://www.pixiv.net/ajax/follow_latest/illust?mode=all&lang=zh&p={page}'
            web_info = self._call_api_get_json(web_url)['body']['page']['ids']
        except Exception as msg:
            raise RuntimeError(f"api获取失败，msg: {msg}")

        # 2. 逐个爬取
        download_cnt = 0
        for illustid in web_info:
            if self.download_by_illustid(illustid):
                download_cnt += 1

        return download_cnt

    def download_by_pixivision_aid(self, aid: int) -> int:
        """
        在www.pixivision.net网站上爬取指定专集插画的所有内容，仅支持插画类，其他类型专集自动跳过

        :return: 返回新增的插画数量
        """
        logger.info(f"调用了 download_by_pixivision_aid({aid})")

        # 0. 检查参数
        if not isinstance(aid, int) or aid <= 0:
            raise ValueError("参数aid错误")

        # 1. 获取网页内容
        try:
            api_url = f"https://www.pixivision.net/zh/a/{aid}"
            web_content = self._web.get(api_url).text()
        except Exception as msg:
            raise RuntimeError(f"网页信息获取失败，msg: {msg}")

        # 2. 解析网页内容
        try:
            parsel_obj = parsel.Selector(web_content)
        except Exception as msg:
            raise RuntimeError(f"网页使用parsel解析失败, msg: {msg}")

        # 3. 获取aid标题和类型
        # 部分aid网页会有问题，指定的aid既存在又显示不正常
        try:
            title = parsel_obj.css('.am__title')[0].root.text
            a_type = parsel_obj.css('.am__categoty-pr').css('a').attrib['data-gtm-label']
        except Exception:
            raise RuntimeError(f"网页解析出现问题，部分class标签不存在于网页上，停止爬取，aid: {aid}")

        # 4. 如果type不是illustration，返回0
        if a_type != 'illustration':
            logger.info(f"该aid不是illustration类型，所以不爬取, aid: {aid}")
            return 0

        # 5. 获取aid的描述内容
        # 如果description无法读取，置为空字符串
        try:
            description = parsel_obj.css('.am__description')[0].root.text_content()
        except Exception as msg:
            logger.info(f"该aid的描述获取失败，所以设为空字符串, aid: {aid}, msg: {msg}")
            description = ''

        # 6. 获取illust列表
        try:
            illust_ids = tuple(
                int(i.css('a').attrib['href'].split('/')[-1])
                for i in parsel_obj.css('.am__body')[0].css('.am__work__main')
            )
        except Exception as msg:
            raise RuntimeError(f"该aid的illustid列表获取失败, aid: {aid}, msg: {msg}")

        # 7. 开始逐一爬取
        illust_list = []
        download_cnt = 0
        with self._sql() as session:
            for i in illust_ids:
                if self.download_by_illustid(i):
                    download_cnt += 1

                illust_list.append(
                    session.query(Illust).where(Illust.illustid == i).one()
                )

        # 8. Pixivision和与illust关联数据信息存数据库
        pixivision = Pixivision(
            aid=aid,
            type=a_type,
            description=description,
            title=title,
            illusts=illust_list
        )
        with self._sql() as session:
            # 如果数据库中存在此条记录 则不insert
            if session.query(Pixivision).where(Pixivision.aid == aid).one_or_none() is None:
                session.add(pixivision)
                session.commit()

        return download_cnt

    def get_info(self):
        # TODO
        class InfoResult(object):
            __slots__ = ()
            @property
            def storage_size(_):
                with self._sql() as session:
                    session: Session
                    session.execute('select SUM(filesize) from illust')

                return 0
            @property
            def storage_path(_):
                return ""
            @property
            def illust_size(_):
                return 0
            @property
            def imgfile_size(_):
                return 0

        return InfoResult()
