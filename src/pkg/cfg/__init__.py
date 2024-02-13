import typing
import pathlib


class PixivConfig(typing.NamedTuple):
    phpsessid: str
    proxy: str
    file_path: pathlib.Path
    sql_url: str


def get_pixiv_config(filename: str = "config.yml") -> PixivConfig:
    import yaml
    filepath = pathlib.Path(__file__).parent.parent.parent / "cfg" / filename
    with open(filepath, "r") as f:
        obj = yaml.safe_load(f)
    return PixivConfig(
        phpsessid=obj["session_id"],
        proxy=obj["proxy"],
        file_path=pathlib.Path(obj["file_path"]),
        sql_url=obj["sql_url"],
    )
