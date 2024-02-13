import pkg.log as log
import pkg.pixivapi as pixiv_api
import pkg.pixivmodel as model
import yaml
from pathlib import Path
import typing

CONFIG = yaml.load(open('cfg/config.yml', 'r'), yaml.CLoader)
FILE_PATH = Path(CONFIG['file_path'])


api = pixiv_api.new_pixiv_api(pixiv_api.ApiMetaArgument(
    PHPSESSID=CONFIG['session_id'],
    PROXY=CONFIG['proxy']
))
sql = model.new_session(CONFIG['sql_url'])


def _new_artwork(
        artwork_info: pixiv_api.ArtworkInfo,
        tags: list[pixiv_api.ArtworkTag],
        file_size: int) -> model.Artwork:
    return model.Artwork(
        artwork_id=artwork_info.artwork_id,
        user_id=artwork_info.user_id,
        artwork_type=artwork_info.artwork_type.value,
        title=artwork_info.title,
        nums=artwork_info.nums,
        restrict=artwork_info.restrict.value,
        description=artwork_info.desc,
        bookmark_cnt=artwork_info.bookmark_cnt,
        like_cnt=artwork_info.like_cnt,
        comment_cnt=artwork_info.comment_cnt,
        view_cnt=artwork_info.view_cnt,
        create_time=artwork_info.create_time,
        upload_time=artwork_info.upload_time,
        height=artwork_info.height,
        width=artwork_info.width,
        file_size=file_size,
        tags=tags
    )


def _get_filepath(artwork_id: int, idx: int) -> Path:
    return FILE_PATH / f"{artwork_id}_{idx}.jpg"


def _download_artwork(artwork_info: pixiv_api.ArtworkInfo) -> int:
    total_file_size = 0
    for idx, url in enumerate(artwork_info.image_download_urls):
        file_path = _get_filepath(artwork_info.artwork_id, idx)
        if file_path.exists() and file_path.stat().st_size > 0:
            total_file_size += file_path.stat().st_size
            continue
        content = api.get_image(url)
        total_file_size += len(content)
        with file_path.open('wb+') as f:
            f.write(content)
    return total_file_size


def is_artwork_exist(artwork_id: int) -> bool:
    with sql() as session:
        artwork_record = session.query(model.Artwork).filter_by(artwork_id=artwork_id).first()
        if not artwork_record:
            return False
    for idx in range(artwork_record.nums):
        file_path = _get_filepath(artwork_id, idx)
        if not file_path.exists() or file_path.stat().st_size <= 0:
            return False
    return True


def _crawler_by_artwork_info(artwork_info: pixiv_api.ArtworkInfo, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    invalid_reason = options.valid_by_artwork_info(artwork_info)
    if invalid_reason:
        log.info(f"artwork {artwork_info.artwork_id} is invalid, reason: {invalid_reason}")
        return

    if is_artwork_exist(artwork_info.artwork_id):
        if not options.update:
            log.info(f"artwork {artwork_info.artwork_id} already exist")
            return
    # 爬取图片
    total_filesize = _download_artwork(artwork_info)
    # 存数据库
    with sql() as session:
        tags = []
        for tag in artwork_info.tags:
            tag_record = session.query(model.Tag).filter_by(name=tag.name).first()
            if tag_record is None:
                tags.append(model.Tag(name=tag.name, trans_name=tag.translation))
            else:
                tags.append(tag_record)
        user = model.User(user_id=artwork_info.user_id, user_name=artwork_info.user_name)
        artwork = _new_artwork(artwork_info, tags, total_filesize)
        session.merge(user)
        session.merge(artwork)  # 会自动插入不存在的tag
        session.commit()
    

def crawler_by_artwork_id(artwork_id: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artwork_info = api.get_artwork_info(artwork_id, options)
    _crawler_by_artwork_info(artwork_info, options)
    log.info(
        f"save artwork {artwork_info.artwork_id} to database",
        title=artwork_info.title,
        tags=[tag.name for tag in artwork_info.tags],
        user=f"{artwork_info.user_name}({artwork_info.user_id})",
    )


def crawler_by_user_id(user_id: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks = api.get_artworks_by_userid(user_id, options)
    log.info(
        f"get {len(artworks)} artworks from user {user_id}",
        artworks=[artwork_info.artwork_id for artwork_info in artworks],
        user_id=user_id
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_pixivision_aid(aid: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    res = api.get_artworks_by_pixivision_aid(aid, options)
    log.info(
        f"get {len(res.artworks)} artworks from pixivision {aid}",
        artworks=[artwork_info.artwork_id for artwork_info in res.artworks],
        title=res.title,
        type=res.pixivision_type,
    )
    for artwork_info in res.artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    pixivision = model.Pixivision(
        aid=aid,
        title=res.title,
        type=res.pixivision_type,
        description=res.desc,
        artworks=[model.Artwork(artwork_id=artwork_info.artwork_id) for artwork_info in res.artworks]
    )
    with sql() as session:
        session.merge(pixivision)
        session.commit()
    log.info(f"save pixivision {aid} to database")


def crawler_by_bookmark_new(page: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks = api.get_artworks_by_bookmark_new(page, options)
    log.info(
        f"get {len(artworks)} artworks from bookmark new",
        artworks=[artwork.artwork_id for artwork in artworks],
        page=page
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_recommend(options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: list[pixiv_api.ArtworkInfo] = api.get_artworks_by_recommend(options)
    log.info(
        f"get {len(artworks)} artworks from recommend",
        artworks=[artwork_info.artwork_id for artwork_info in artworks]
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_rank(rank_type: pixiv_api.RankType, date: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: list[pixiv_api.ArtworkInfo] = api.get_artworks_by_rank(rank_type, date, options)
    log.info(
        f"get {len(artworks)} artworks from rank",
        artworks=[artwork_info.artwork_id for artwork_info in artworks],
        rank_type=rank_type.name,
        date=date
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_request_recommend(options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: list[pixiv_api.ArtworkInfo] = api.get_artworks_by_request_recommend(options)
    log.info(
        f"get {len(artworks)} artworks from request recommend",
        artworks=[artwork_info.artwork_id for artwork_info in artworks]
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_user_bookmark(user_id: int, page: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: list[pixiv_api.ArtworkInfo] = api.get_artworks_by_user_bookmark(user_id, page, options)
    log.info(
        f"get {len(artworks)} artworks from user bookmark",
        artworks=[artwork_info.artwork_id for artwork_info in artworks],
        user_id=user_id,
        page=page
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_tag_popular(tag_name: str, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: list[pixiv_api.ArtworkInfo] = api.get_artworks_by_tag_popular(tag_name, options)
    log.info(
        f"get {len(artworks)} artworks from tag popular",
        artworks=[artwork_info.artwork_id for artwork_info in artworks],
        tag_name=tag_name
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_similar_artwork(artwork_id: int, options: pixiv_api.ArtworkOptions = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: list[pixiv_api.ArtworkInfo] = api.get_artworks_by_similar_artwork(artwork_id, options)
    log.info(
        f"get {len(artworks)} artworks from similar artwork_info",
        artworks=[artwork_info.artwork_id for artwork_info in artworks],
        artwork_id=artwork_id
    )
    for artwork_info in artworks:
        _crawler_by_artwork_info(artwork_info, options)
        log.info(
            f"save artwork {artwork_info.artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
        )
    log.info(f"save {len(artworks)} artworks to database")


def crawler_by_similar_user(user_id: int, options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    userids: list[int] = api.get_userids_by_similar_user(user_id, options)
    log.info(
        f"get {len(userids)} similar user from user {user_id}",
        userids=userids,
        user_id=user_id
    )
    for userid in userids:
        crawler_by_user_id(userid, options)
    log.info(f"save {len(userids)} similar user to database")


def crawler_by_recommend_user(options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    userids: list[int] = api.get_userids_by_recommend(options)
    log.info(
        f"get {len(userids)} recommend user",
        userids=userids
    )
    for userid in userids:
        crawler_by_user_id(userid, options)
    log.info(f"save {len(userids)} recommend user to database")


def crawler_by_request_creater(options: pixiv_api.ArtworkOptions=None):
    if options is None:
        options = pixiv_api.new_filter()

    userids: list[int] = api.get_userids_by_request_creator(options)
    log.info(
        f"get {len(userids)} request creater",
        userids=userids
    )
    for userid in userids:
        crawler_by_user_id(userid, options)
    log.info(f"save {len(userids)} request creater to database")
