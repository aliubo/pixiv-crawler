from loguru import logger
import os
import sys
from pathlib import Path
import command
from utils.fileio_factory import FileIOFactory


WORK_DIRECTORY = Path(__file__).resolve().parent
os.chdir(WORK_DIRECTORY)

logger.configure(handlers=[{"sink":sys.stdout, "level":"ERROR"}])
config_dir = FileIOFactory()
config_dir.setRootPath(Path('resource/config'))
config_dir = config_dir.generate()
config: dict = config_dir.open_read_yaml('config.yaml')


def setup_custom_logger():
    logger.configure(**{
        "handlers":[
            {
                "sink": sys.stdout,
                "format": "<g>{time}</g> <lw>|</lw> <lvl>{level}</lvl> <lw>|</lw> "
                          "<le>{file}</le>:<le>{line}</le> <lw>- {message}</lw>",
                "level": config['log']['stdout_level'],
                "colorize": True
            },
            {
                "sink": config['log']['file_location'],
                "level": config['log']['file_level'],
                "format": "{time} | {level} | {file}:{line} - {message}",
                "rotation": "10MB",         # 达到什么条件后分文件归档
                "retention": 10,            # 删除超过指定数量的归档文件
                "compression": "zip"        # 归档后自动压缩
            }
        ]
    })
    # logger.add(
    #     "../log/running_{time}.log",
    #     rotation="1h",
    #     format="{time} - {level} - {file}:{line} - {message}",
    #     level="INFO",
    #     compression="zip"
    # )
    # 等同于以下dict配置，由logger.configure解析执行
    # {
    #     "sink": "../log/running_{time}.log",
    #     "rotation": "1h",
    #     "format": "{time} - {level} - {file}:{line} - {message}",
    #     "level": "INFO",
    #     "compression": "zip"
    # }


def main():
    # 配置log
    setup_custom_logger()

    logger.info("start.py 主程序启动, Version: ")

    # 读取命令行参数，并执行command的主模块
    args = sys.argv[1:]
    if len(args) > 0:
        print('$ ' + ' '.join(args))
        command.run(args)
    else:
        command.run()


if __name__ == '__main__':
    main()
