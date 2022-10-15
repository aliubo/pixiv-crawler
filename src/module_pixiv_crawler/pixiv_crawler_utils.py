from loguru import logger
from PIL import Image
from enum import Enum


"""
图片相关工具
"""


class ThumbnailLevelEnum(Enum):
    X256 = 256
    X512 = 512
    X1024 = 1024
    X2048 = 2048


def get_thumbnail_img(input_filepath, output_filepath, level: ThumbnailLevelEnum) -> bytes:
    img = Image.open(input_filepath)
    img.thumbnail((level.value,) * 2)
    img.save(output_filepath, 'jpeg')
    return img.tobytes()
