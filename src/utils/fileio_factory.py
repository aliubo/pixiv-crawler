from loguru import logger
import json
from pathlib import Path, PurePath
import yaml


class FileIO(object):
    __slots__ = '_directory'

    def __init__(self, directory):
        self._directory = directory

    def get_directory(self):
        return self._directory

    def open(self, file, mode='r', buffering=None, encoding=None, errors=None, newline=None, closefd=True):
        """
        用于打开一个文件，原理是调用python内置open函数以打开，可以加with as自动关闭

        :param file: str或bytes表示的相对路径，或者是用os.PurePath()包装的相对路径
        :return: 返回打开的标准python文件对象
        """
        filename = self._directory / PurePath(file)
        return open(filename, mode, buffering, encoding, errors, newline, closefd)

    def open_read_bytes(self, file) -> bytes:
        """
        简易操作函数，读取文件的所有字节并返回字节数组

        :param file: str或bytes表示的相对路径，或者是用os.PurePath()包装的相对路径
        :return: 返回指定文件的字节数组
        """
        logger.debug(f"以二进制的方式打开了 {file}")
        return (self._directory / PurePath(file)).read_bytes()

    def open_read_str(self, file, encoding='utf_8') -> str:
        logger.debug(f"以字符串{encoding}的方式读取了 {file}")
        return (self._directory / PurePath(file)).read_text(encoding=encoding)

    def open_read_json(self, file, encoding='utf_8') -> dict | list | str | int | float | bool | None:
        res = json.loads(self.open_read_str(file, encoding))
        logger.debug(f"以json的方式读取了{file}")
        return res

    def open_read_yaml(self, file, encoding='utf_8') -> dict | list | str | int | float | bool | None:
        res = yaml.load(self.open_read_str(file, encoding), yaml.CLoader)
        logger.debug(f"以yaml读取了{file}")
        return res

    def open_overwrite_bytes(self, file, data: bytes):
        logger.debug(f"覆写了二进制文件 {file}")
        with (self._directory / PurePath(file)).open('wb+') as f:
            f.write(data)

    def open_overwrite_str(self, file, text: str, encoding='utf_8'):
        with (self._directory / PurePath(file)).open('w+', encoding=encoding) as f:
            f.write(text)

    def open_append_bytes(self, file, data: bytes):
        logger.debug(f"追加了二进制编码文件 {file}")
        with (self._directory / PurePath(file)).open('ab') as f:
            f.write(data)

    def open_append_str(self, file, text: str, encoding='utf_8'):
        logger.debug(f"以{encoding}编码追加了字符串文件 {file}")
        with (self._directory / PurePath(file)).open('a', encoding=encoding) as f:
            f.write(text)

    def is_exist(self, file):
        return (self._directory / PurePath(file)).exists()

    def is_file(self, file):
        return (self._directory / PurePath(file)).is_file()

    def is_dir(self, file):
        return (self._directory / PurePath(file)).is_dir()


class FileIOFactory(object):
    """
    关于文件管理的工厂，整个类实现基于pathlib模块，面向对象的文件系统路径
    """
    __slots__ = ('_root_dir', '_dir_tree')

    def __init__(self):
        self._root_dir = Path('.')
        self._dir_tree = {}

    def setRootPath(self, directory: str | Path) -> None:
        path = Path(directory)
        if not path.exists():
            raise AttributeError("参数directory所指的目录不存在")
        if not path.is_dir():
            raise AttributeError("参数directory所指向的不是一个目录")
        self._root_dir = path

    def setDirectoryTree(self, directory_tree: dict) -> None:
        """
        设置文件夹树，创建对象时自动生成

        :param directory_tree:
        :return:
        """
        self._dir_tree = directory_tree

    def _generate_directory_tree(self, current_path: Path, directory_tree: dict) -> None:
        """
        创建目录树结构，如果目录不存在的话
        directory_tree举例：
        {
            'a': None,
            'b': {
                'c': None
                'd': None
            }
        }

        :param current_path: 根目录的路径
        :param directory_tree: dict格式，值可以是dict或None，若是dict则是字目录树的结构
        """
        if directory_tree is None:
            return
        for i in directory_tree:
            directory = current_path / i
            if not directory.exists():
                directory.mkdir()
            if not directory.is_dir():
                raise RuntimeError(f"{directory.absolute()} 该路径已存在，但不是目录")
            self._generate_directory_tree(directory, directory_tree[i])

    def generate(self) -> FileIO:
        """
        开始利用工厂模式生成一个FileIO对象

        :return: 基于配置生成的一个FileIO对象
        """
        self._generate_directory_tree(self._root_dir, self._dir_tree)
        return FileIO(self._root_dir)
