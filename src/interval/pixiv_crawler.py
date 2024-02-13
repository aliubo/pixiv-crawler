import pkg.log as log
import pkg.pixivapi as pixiv_api
import pkg.pixivmodel as model
import pkg.cfg as cfg
import yaml
from pathlib import Path


config = cfg.get_pixiv_config()


api = pixiv_api.new_pixiv_api(pixiv_api.ApiMetaArgument(
    PHPSESSID=config.phpsessid,
    PROXY=config.proxy
))
sql = model.new_session(config.sql_url)


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
    return config.file_path / f"{artwork_id}_{idx}.jpg"


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


def _is_artwork_exist(artwork_id: int) -> bool:
    with sql() as session:
        artwork_record = session.query(model.Artwork).filter_by(artwork_id=artwork_id).first()
        if not artwork_record:
            return False
    for idx in range(artwork_record.nums):
        file_path = _get_filepath(artwork_id, idx)
        if not file_path.exists() or file_path.stat().st_size <= 0:
            return False
    return True


def _crawler_by_artwork_info(
        artwork_info: pixiv_api.ArtworkInfo,
        options: pixiv_api.ArtworkOptions | None = None) -> bool:
    if options is None:
        options = pixiv_api.new_filter()

    invalid_reason = options.valid_by_artwork_info(artwork_info)
    if invalid_reason:
        log.info(f"artwork {artwork_info.artwork_id} is invalid, reason: {invalid_reason}")
        return False

    if _is_artwork_exist(artwork_info.artwork_id):
        if not options.update:
            log.info(f"artwork {artwork_info.artwork_id} already exist")
            return False
    # 爬取图片
    total_file_size = _download_artwork(artwork_info)
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
        artwork = _new_artwork(artwork_info, tags, total_file_size)
        session.merge(user)
        session.merge(artwork)  # 会自动插入不存在的tag
        session.commit()
    return True


def _crawler_by_artworks_info(
        artworks_info: dict[int, pixiv_api.ArtworkInfo],
        options: pixiv_api.ArtworkOptions) -> list[int]:
    log.info("Artworks start downloading...", artworks=artworks_info.keys())
    ok_ids = []
    for idx, (artwork_id, artwork_info) in enumerate(artworks_info.items()):
        log.info(f"{idx+1}/{len(artworks_info)} - {artwork_id}")
        try:
            if _crawler_by_artwork_info(artwork_info, options):
                ok_ids.append(artwork_id)
        except Exception as e:
            log.error(f"save artwork {artwork_id} failed", error=str(e))
            if not options.ignore_error:
                raise e
            continue
        log.info(
            f"save artwork {artwork_id} to database",
            title=artwork_info.title,
            tags=[tag.name for tag in artwork_info.tags],
            user=f"{artwork_info.user_name}({artwork_info.user_id})",
            nums=artwork_info.nums
        )
    log.info("Artworks download finished", failed_ids=[i for i in artworks_info.keys() if i not in ok_ids])
    return ok_ids


def crawler_by_artwork_id(artwork_id: int, options: pixiv_api.ArtworkOptions | None = None):
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


def crawler_by_user_id(user_id: int, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()
    artworks = api.get_artworks_by_userid(user_id, options)
    log.info("get artworks from user", user_id=user_id)
    _crawler_by_artworks_info(artworks, options)


def _crawler_by_users_id(user_ids: list[int], options: pixiv_api.ArtworkOptions):
    log.info("Users start downloading...", user_ids=user_ids)
    for idx, user_id in enumerate(user_ids):
        log.info(f"! {idx + 1}/{len(user_ids)} start to save user {user_id} to database")
        crawler_by_user_id(user_id, options)
    log.info("Users download finished")


def crawler_by_pixivision_aid(aid: int, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    res = api.get_artworks_by_pixivision_aid(aid, options)
    log.info(f"get artworks from pixivision", aid=aid, title=res.title, type=res.pixivision_type)
    crawler_ids = _crawler_by_artworks_info(res.artworks, options)
    with sql() as session:
        pixivision = model.Pixivision(
            aid=aid,
            title=res.title,
            type=res.pixivision_type,
            description=res.desc,
            artworks=[
                session.query(model.Artwork).filter_by(artwork_id=artwork_id).first()
                for artwork_id in crawler_ids
            ]
        )
        session.merge(pixivision)
        session.commit()
    log.info(f"save pixivision {aid} to database")


def crawler_by_follow_latest(page: int, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks = api.get_artworks_by_follow_latest(page, options)
    log.info(f"get artworks from bookmark new", page=page)
    _crawler_by_artworks_info(artworks, options)


def crawler_by_recommend(options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: dict[int, pixiv_api.ArtworkInfo] = api.get_artworks_by_recommend(options)
    log.info(f"get artworks from recommend")
    _crawler_by_artworks_info(artworks, options)


def crawler_by_rank(rank_type: pixiv_api.RankType, date: int, page: int, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: dict[int, pixiv_api.ArtworkInfo] = api.get_artworks_by_rank(rank_type, date, page, options)
    log.info(f"get artworks from rank", rank_type=rank_type.name, date=date, page=page)
    _crawler_by_artworks_info(artworks, options)


def crawler_by_request_recommend(options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: dict[int, pixiv_api.ArtworkInfo] = api.get_artworks_by_request_recommend(options)
    log.info(f"get artworks from request recommend")
    _crawler_by_artworks_info(artworks, options)


def crawler_by_user_bookmark(user_id: int, page: int, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: dict[int, pixiv_api.ArtworkInfo] = api.get_artworks_by_user_bookmark(user_id, page, options)
    log.info(f"get artworks from user bookmark", user_id=user_id, page=page)
    _crawler_by_artworks_info(artworks, options)


def crawler_by_tag_popular(tag_name: str, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: dict[int, pixiv_api.ArtworkInfo] = api.get_artworks_by_tag_popular(tag_name, options)
    log.info(f"get artworks from tag popular", tag_name=tag_name)
    _crawler_by_artworks_info(artworks, options)


def crawler_by_similar_artwork(artwork_id: int, options: pixiv_api.ArtworkOptions = None):
    if options is None:
        options = pixiv_api.new_filter()

    artworks: dict[int, pixiv_api.ArtworkInfo] = api.get_artworks_by_similar_artwork(artwork_id, options)
    log.info(f"get artworks from similar artwork_info", artwork_id=artwork_id)
    _crawler_by_artworks_info(artworks, options)


def crawler_by_similar_user(user_id: int, options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    userids: list[int] = api.get_userids_by_similar_user(user_id, options)
    log.info(f"get similar user from user {user_id}", user_id=user_id)
    _crawler_by_users_id(userids, options)


def crawler_by_recommend_user(options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    userids: list[int] = api.get_userids_by_recommend(options)
    log.info(f"get recommend user")
    _crawler_by_users_id(userids, options)


def crawler_by_request_creator(options: pixiv_api.ArtworkOptions | None = None):
    if options is None:
        options = pixiv_api.new_filter()

    userids: list[int] = api.get_userids_by_request_creator(options)
    log.info(f"get request creator")
    _crawler_by_users_id(userids, options)
