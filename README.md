# pixiv_crawler

爬取pixiv网站的图片，支持多种爬取模式：  

## 功能

* 按illustid（artworksid）爬取  
* 按userid爬取
* 按pixivisionId爬取（pixivision网站）
* 爬取已关注用户的最新作品
* 不支持爬取动图

## 使用方法

### 源代码如何使用

1. 解压
2. 配置文件 src/resource/config/config_pixiv_crawler.yaml（可以直接复制同级文件夹下的config_pixiv_crawler.yaml.bak使用）
3. 在根目录下命令行执行`python main.py`
4. 进入程序内命令行，开始使用

### 如何使用

* `help`查看帮助
* `auto <url> [<url> [<url> ...]]` 根据url地址形式自动下载，可以直接输入多个。支持以下url形式：https://www.pixiv.net/artworks/123456, https://www.pixiv.net/users/123456, https://www.pixivision.net/zh/a/123。如果链接是一个画师链接则自动下载全部作品
* `update` 自动爬取已关注用户的最新作品, 直到超出页数限制或者电脑已爬取过之前的图片为止