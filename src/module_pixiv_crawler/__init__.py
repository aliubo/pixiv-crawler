"""
module_pixiv_crawler包介绍

.pixiv_crawler_connection 一切外界python文件应调用这个模块实现，与外界的接口
.pixiv_crawler_model      ORM
.pixiv_crawler_service    基础功能服务实现，如爬取、读图、缩略图等操作
.pixiv_crawler_utils      为本包里其他模块提供一些常用方法

本包仅用作SDK为外部提供服务
"""