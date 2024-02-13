import os

os.chdir('./src')


SQL_TYPE_MAP = [
    ("mysql", "mysql+mysqlconnector", 3306),
    ("sqlite", "sqlite", 0),
    ("postgresql", "postgresql", 5432),
]
SQL_TYPE_MAP_NAME = 0
SQL_TYPE_MAP_URL_PREFIX = 1
SQL_TYPE_MAP_DEFAULT_PORT = 2


if not os.path.exists("cfg/config.yml"):
    print(
        "Config file not found. Start initialization process..\n"
        "配置文件未找到，开始初始化流程\n\n"
    )

    file_path = input(
        "输入图片文件保存路径/Enter file save path\n"
        "默认/Default: ../file\n"
        "> ").strip()
    if not file_path:
        file_path = "../file"
    if not os.path.exists(file_path):
        print("路径不存在/Path not exists")
        exit(1)

    session_id = input("输入Pixiv PHPSESSID/Enter Pixiv PHPSESSID\n> ").strip()
    if not session_id:
        print("输入错误/Invalid input")
        exit(1)

    use_proxy = input("是否使用代理/Use proxy? (y/n)\n> ").strip()
    if use_proxy.lower() == "y":
        proxy_url = input("输入代理地址和端口/Enter proxy address(e.g. 127.0.0.1:7890)\n> ").strip()
        if not proxy_url:
            print("输入错误/Invalid input")
            exit(1)
    else:
        proxy_url = ""

    sql_type_idx = input(
        "输入数据库类型/Enter database type\n" +
        "\n".join([f"{i + 1}. {v[SQL_TYPE_MAP_NAME]}" for i, v in enumerate(SQL_TYPE_MAP)]) + "\n" +
        "> "
    ).strip()
    if not sql_type_idx.isdigit() or int(sql_type_idx) not in range(1, len(SQL_TYPE_MAP) + 1):
        print("输入错误/Invalid input")
        exit(1)
    sql_type_idx = int(sql_type_idx) - 1
    sql_type, sql_url_prefix, _ = SQL_TYPE_MAP[sql_type_idx]
    if sql_type in ("sqlite", ):
        sql_file_path = input(
            "输入数据库文件保存路径/Enter database file save path\n"
            "默认/Default: ../db.sqlite\n"
            "> "
        ).strip()
        if not sql_file_path:
            sql_file_path = "../db.sqlite"
        sql_url = f"{sql_url_prefix}:///{sql_file_path}"
    else:
        sql_addr = input(
            "输入数据库连接地址/Enter database connection address\n"
            "默认/Default: localhost\n"
            "> ").strip()
        if not sql_addr:
            sql_addr = "localhost"
        sql_port = input(
            "输入数据库端口/Enter database port\n"
            f"默认/Default: {SQL_TYPE_MAP[sql_type_idx][SQL_TYPE_MAP_DEFAULT_PORT]}\n"
            "> "
        ).strip()
        if not sql_port:
            sql_port = SQL_TYPE_MAP[sql_type_idx][SQL_TYPE_MAP_DEFAULT_PORT]
        sql_user = input("输入数据库用户名/Enter database username\n> ").strip()
        sql_pwd = input("输入数据库密码/Enter database password\n> ").strip()
        sql_db = input("输入数据库名称/Enter database name\n> ").strip()
        sql_url = f"{sql_url_prefix}://{sql_user}:{sql_pwd}@{sql_addr}:{sql_port}/{sql_db}"

    file_content = (
        f"file_path: {file_path}\n"
        f"session_id: {session_id}\n"
        f"proxy: {proxy_url}\n"
        f"sql_url: {sql_url}\n"
    )
    with open("cfg/config.yml", "w", encoding="utf-8") as f:
        f.write(file_content)
    print(
        "配置信息已保存，以下是配置内容/Config saved, following is the content:\n"
        "---------------\n"
        f"{file_content}\n"
        "---------------\n"
        "修改配置文件/src/cfg/config.yml可重新调整，或直接删除该文件后重新进行初始化流程\n"
        "Modify /src/cfg/config.yml to adjust the config, or delete the file and re-run this script\n\n"
    )
    run = input("是否立即运行/Run now? (y/n)\n> ").strip()
    if run.lower() != "y":
        exit()

os.system("python3 run.py")
