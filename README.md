# pixiv_crawler

爬取pixiv网站的图片，支持多种爬取模式：  

## 功能

* 按照artwork id下载图片
* 按照画师id(userid)下载图片
* 按照pixivision id下载图片(pixvision站)
* 按照关注的画师最新上传下载图片
* 按照首页推荐的作品下载图片
* 按照排行榜下载图片
* 按照接稿的推荐作品下载图片
* 按照用户的收藏下载图片
* 按照指定标签的热门作品下载图片
* 按照指定的artwork id的相似作品下载图片
* 按照指定的画师id的所有相似画师下载图片
* 按照平台推荐的画师下载图片
* 按照接稿的最新接稿画师下载图片

## 使用方法

### 源代码如何使用

1. 找到合适的地方，下载源代码 
> `git clone https://github.com/aliubo/pixiv-crawler.git`

2. 运行`python3 main.py`
3. 第一次运行会有提示向导，根据提示输入PHPSESSID、数据库信息、下载地址、代理地址
4. DOTO
