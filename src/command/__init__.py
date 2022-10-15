import traceback
from importlib import import_module
from loguru import logger


def order_run(args):
    if len(args) == 0:
        print("run指令必须要有参数")
        return

    module_name = f"command.command_{args[0]}"
    logger.debug(f"命令行加载 {module_name} 模块")

    try:
        pkg = import_module(module_name)
    except Exception as msg:
        logger.debug(f"用户尝试 run 实际不存在的 {module_name} 模块，msg:{msg}")
        return

    try:
        pkg.run(args[1:])
    except Exception as msg:
        stackinfo = traceback.format_exc().replace('\n', ' ')
        logger.error(
            f"指令遇到错误，异常被捕获, "
            f"module: {module_name}, "
            f"msg: {msg}, "
            f"traceback: {stackinfo}"
        )


def process_one_line(args):
    if len(args) == 0:
        return

    if args[0] == 'run':
        order_run(args[1:])

    else:
        print("未知指令，输入help查看帮助")


def run(args = None):
    if args is not None:
        process_one_line(args)

    while True:
        line = input('$ ').strip().split(' ')
        line = list(filter(lambda x: x != '', line))

        if len(line) == 0:
            continue

        if line[0] == 'exit':
            break

        process_one_line(line)
