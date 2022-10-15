from loguru import logger
import traceback
from pathlib import Path
from module_pixiv_crawler.pixiv_crawler_connection import connect
from utils.fileio_factory import FileIOFactory

__all__ = 'run'

config_dir = FileIOFactory()
config_dir.setRootPath(Path('resource/config'))
config_dir = config_dir.generate()
pixiv_config: dict = config_dir.open_read_yaml('config_pixiv_crawler.yaml')


class PixivCrawlerCommand(object):
    def __init__(self, env):
        self.service = connect(
            pixiv_config[env]['sql_url'],
            pixiv_config[env]['file_path'],
            pixiv_config[env]['session_id'],
            pixiv_config[env]['proxy'],
            pixiv_config[env]['timezone']
        )

    @staticmethod
    def help():
        print(
            "help帮助\n"
            "---------\n"
            "help \t\t\t获取帮助\n"
            "auto [<addr>, ...] \t自动根据链接地址进行爬取\n"
            "a \t\t\t同auto\n"
            "update \t\t\t自动更新已关注作者的作品\n"
            "u \t\t\t同update\n"
            "user [<id>, ...] \t根据userid下载画师的所有作品\n"
            "illust [<id>, ...] \t根据artworkid下载对应插画\n"
        )

    def auto_crawler(self, li):
        if len(li) == 0:
            print("需提供参数")
            return
        # 针对于www.pixiv.net站点
        for i in li:
            j = i.split('/')
            failed_info = f"提取链接信息失败，url: {i}"
            j = j + ['']*5   # 防止index of out range

            if j[2] == 'www.pixiv.net':
                j = j[3:]
                if j[0] in ('en', 'zh'):    # 去掉https://www.pixiv.net/en/XXX的en | zh
                    j = j[1:]
                # 逐一判断
                if j[0] == 'artworks':
                    self.service.download_by_illustid(int(j[1]))
                    print(f"illustid: {j[1]} 爬取完毕")
                elif j[0] == 'users':
                    res = self.service.download_by_userid(int(j[1]))
                    print(f"userid: {j[1]} 爬取完毕，共爬取了{res}张插画")
                else:
                    print(failed_info)
                    logger.info(failed_info)
                    return

            elif j[2] == 'www.pixivision.net':
                j = j[3:]
                if j[0] in ('en', 'zh'):    # 去掉https://www.pixivision.net/zh/XXX的en | zh
                    j = j[1:]
                if j[0] == 'a':
                    res = self.service.download_by_pixivision_aid(int(j[1]))
                    print(f"pixivision aid: {j[1]} 爬取完毕，共爬取了{res}张插画")
                else:
                    print(failed_info)
                    logger.info(failed_info)
                    return

            else:
                print(failed_info)
                logger.info(failed_info)
                return

    def illust_crawler(self, li):
        if len(li) == 0:
            print("需提供参数")
            return
        download_cnt = 0
        for i in li:
            print(f"正在爬取illustid = {i}")
            if self.service.download_by_illustid(int(i)):
                download_cnt += 1
        print(f"完成，新增{download_cnt}条illust数据")

    def user_crawler(self, li):
        if len(li) == 0:
            print("需提供参数")
            return
        download_cnt = 0
        for i in li:
            print(f"正在爬取userid = {i}")
            download_cnt += self.service.download_by_userid(int(i))
        print(f"完成，新增{download_cnt}条illust数据")

    def pixivision_crawler(self, li):
        if len(li) == 0:
            print("需提供参数")
            return
        download_cnt = 0
        for i in li:
            print(f"正在爬取aid = {i}")
            download_cnt += self.service.download_by_pixivision_aid(int(i))
        print(f"完成，新增{download_cnt}条illust数据")

    def update_crawler(self):
        page_idx = 0
        page_limit = 30
        download_cnt = 0
        while True:
            page_idx += 1
            if page_idx > page_limit:   # pixiv限制34页
                logger.warning(f"超过{page_limit}页，已自动停止工作，建议遍历所有已关注的画师逐一爬取")
                break
            cnt = self.service.download_by_bookmark_new(page_idx)
            if cnt == 0:
                break
            download_cnt += cnt
        print(f"完成，新增{download_cnt}条illust数据")

    def info(self):
        # TODO
        pass

    def run(self):
        # 开始获取 module_pixiv_crawler.service 的 Service对象
        # 对象通过 module_pixiv_crawler.connection 的 connect实现
        while True:
            # 过滤
            line = input("pixiv_crawler$ ").strip().split(' ')
            line = list(filter(lambda x: x != '', line))
            if len(line) == 0:
                continue

            # 判断指令
            try:
                if line[0] == 'exit':
                    break
                elif line[0] == 'a' or line[0] == 'auto':
                    self.auto_crawler(line[1:])
                elif line[0] == 'u' or line[0] == 'update':
                    self.update_crawler()
                elif line[0] == 'illust':
                    self.illust_crawler(line[1:])
                elif line[0] == 'user':
                    self.user_crawler(line[1:])
                elif line[0] == 'info':
                    self.info()
                elif line[0] == 'h' or line[0] == 'help':
                    self.help()
                else:
                    print("未知指令，输入help查看帮助")
            except Exception as msg:
                print("指令遇到错误，异常被捕获，请检查日志文件以排查产生异常的原因")
                stackinfo = traceback.format_exc().replace('\n', ' ')
                logger.error(
                    f"指令遇到错误，异常被捕获, "
                    f"command: {line}, "
                    f"msg: {msg}, "
                    f"traceback: {stackinfo}"
                )

            # 当任务执行完毕后给出声音提示以示完成
            print("\a")


def run(args):
    if len(args) > 0:
        logger.info("pivix_crawler开始运行")
        PixivCrawlerCommand(args[0]).run()
        logger.info("pivix_crawler结束运行")
    else:
        logger.info("没有输入运行环境名称")
