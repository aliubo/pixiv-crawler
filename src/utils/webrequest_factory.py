from loguru import logger
import requests

__all__ = 'WebRequestFactory'


class Response(object):
    __slots__ = '_resp'

    def __init__(self, resp: requests.Response):
        self._resp: requests.Response = resp

    def text(self) -> str:
        return self._resp.text

    def json(self):
        return self._resp.json()

    def bytes(self) -> bytes:
        return self._resp.content

    def status_code(self) -> int:
        return self._resp.status_code


class WebRequest(object):
    __slots__ = '_session'

    def __init__(self, session: requests.Session):
        self._session = session

    def __del__(self):
        self._session.close()

    def request(self, method, url, params=None, data=None, files=None, json=None,
                allow_redirecrs=True, headers=None, auth=None, varify=None, cert=None, timeout=None) -> Response:
        resp = self._session.request(
            method=method,  # str:  HTTP请求方法
            url=url,  # str:  Url地址
            params=params,  # dict: 查询字符串
            data=data,  # dict | bytes | file-like: body数据
            json=json,  # dict | list: body 存放的json数据
            files=files,    #
            allow_redirects=allow_redirecrs,  # bool: 是否允许重定向
            headers=headers,  # dict
            timeout=timeout,  #
            auth=auth,  #
            verify=varify,  #
            cert=cert  #
        )
        return Response(resp)

    def get(self, url, **kwargs) -> Response:
        """
        使用GET方式进行HTTP请求

        :param url:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("GET", url, allow_redirecrs=True, **kwargs)

    def options(self, url, **kwargs) -> Response:
        """
        使用OPTIONS方式进行HTTP请求

        :param url:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("GET", url, allow_redirecrs=True, **kwargs)

    def head(self, url, **kwargs) -> Response:
        """
        使用HEAD方式进行HTTP请求

        :param url:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("HEAD", url, allow_redirecrs=False, **kwargs)

    def post(self, url, data=None, json=None, **kwargs) -> Response:
        """
        使用POST方式进行HTTP请求

        :param url:
        :param data:
        :param json:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs) -> Response:
        """
        使用PUT方式进行HTTP请求

        :param url:
        :param data:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("PUT", url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs) -> Response:
        """
        使用PATCH方式进行HTTP请求

        :param url:
        :param data:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("PATCH", url, data=data, **kwargs)

    def delete(self, url, **kwargs) -> Response:
        """
        使用DELETE方式进行HTTP请求

        :param url:
        :param kwargs: kwargs所有参数参见 self.request() 方法的参数列表
        """
        return self.request("DELETE", url, **kwargs)


class WebRequestFactory(object):
    __slots__ = ('_cookies', '_headers', '_proxy')

    def __init__(self):
        self._cookies = {}
        self._headers = {}
        self._proxy = {}

    def addCookie(self, key: str, val: str):
        self._cookies[key] = val

    def addCookies(self, cookies: dict[str, str]):
        for i in cookies:
            self.addCookie(i, cookies[i])

    def addHeader(self, key, val):
        self._headers[key] = val

    def addHeaders(self, headers: dict[str, str]):
        for i in headers:
            self.addHeader(i, headers[i])

    def addProxy(self, host):
        self._proxy['http'] = host
        self._proxy['https'] = host

    def generate(self):
        session = requests.session()
        for i in self._headers:
            session.headers[i] = self._headers[i]
        for i in self._proxy:
            session.proxies[i] = self._proxy[i]
        for i in self._cookies:
            session.cookies.set(i, self._cookies[i])
        return WebRequest(session)
