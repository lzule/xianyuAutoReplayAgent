"""闲鱼网页接口封装。"""

from __future__ import annotations

import json
import logging
import ssl
import time
from urllib import parse, request

from app.channel.xianyu_utils import cookies_to_header, generate_sign, parse_cookies


class XianyuApiClient:
    REQUIRED_COOKIE_FIELDS = ("_m_h5_tk", "unb", "cookie2", "sgcookie", "cna")

    def __init__(
        self,
        cookies_str: str,
        *,
        use_system_proxy: bool = False,
        user_agent: str = "Mozilla/5.0",
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.cookies = parse_cookies(cookies_str)
        self.cookie_header = cookies_to_header(self.cookies)
        self.use_system_proxy = use_system_proxy
        self.user_agent = user_agent
        handlers: list[request.BaseHandler] = []
        if not use_system_proxy:
            handlers.append(request.ProxyHandler({}))
        handlers.append(request.HTTPSHandler(context=ssl.create_default_context()))
        self.opener = request.build_opener(*handlers)

    def get_cookie_health(self) -> dict[str, object]:
        missing_fields = [field for field in self.REQUIRED_COOKIE_FIELDS if not self.cookies.get(field)]
        token_value = self.cookies.get("_m_h5_tk", "")
        token_prefix = token_value.split("_", 1)[0] if token_value else ""
        return {
            "loaded": bool(self.cookie_header),
            "length": len(self.cookie_header),
            "missing_fields": missing_fields,
            "has_token_prefix": bool(token_prefix),
            "field_count": len(self.cookies),
        }

    def _post_json(self, url: str, params: dict[str, str], data: dict[str, str], headers: dict[str, str]) -> dict:
        query = parse.urlencode(params)
        body = parse.urlencode(data).encode("utf-8")
        req = request.Request(f"{url}?{query}", data=body, headers=headers, method="POST")
        with self.opener.open(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_token(self, device_id: str) -> dict:
        timestamp = str(int(time.time()) * 1000)
        token = self.cookies.get("_m_h5_tk", "").split("_")[0]
        data_value = json.dumps(
            {"appKey": "444e9908a51d1cb236a27862abc769c9", "deviceId": device_id},
            separators=(",", ":"),
        )
        params = {
            "jsv": "2.7.2",
            "appKey": "34839810",
            "t": timestamp,
            "sign": generate_sign(timestamp, token, data_value),
            "v": "1.0",
            "type": "originaljson",
            "accountSite": "xianyu",
            "dataType": "json",
            "timeout": "20000",
            "api": "mtop.taobao.idlemessage.pc.login.token",
            "sessionOption": "AutoLoginOnly",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.goofish.com",
            "Referer": "https://www.goofish.com/",
            "Host": "h5api.m.goofish.com",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": self.user_agent,
            "Cookie": self.cookie_header,
        }
        return self._post_json(
            "https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/",
            params=params,
            data={"data": data_value},
            headers=headers,
        )

    def get_item_info(self, item_id: str) -> dict:
        timestamp = str(int(time.time()) * 1000)
        token = self.cookies.get("_m_h5_tk", "").split("_")[0]
        data_value = json.dumps({"itemId": item_id}, separators=(",", ":"))
        params = {
            "jsv": "2.7.2",
            "appKey": "34839810",
            "t": timestamp,
            "sign": generate_sign(timestamp, token, data_value),
            "v": "1.0",
            "type": "originaljson",
            "accountSite": "xianyu",
            "dataType": "json",
            "timeout": "20000",
            "api": "mtop.taobao.idle.pc.detail",
            "sessionOption": "AutoLoginOnly",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.goofish.com",
            "Referer": "https://www.goofish.com/",
            "Host": "h5api.m.goofish.com",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": self.user_agent,
            "Cookie": self.cookie_header,
        }
        return self._post_json(
            "https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/",
            params=params,
            data={"data": data_value},
            headers=headers,
        )
