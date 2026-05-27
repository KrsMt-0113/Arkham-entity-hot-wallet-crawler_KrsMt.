"""Arkham 地址标签查询 SDK。"""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any
from urllib.parse import urlparse

import requests

ARKHAM_API_BASE = "https://api.arkm.com"
ARKHAM_WEBAPP_CLIENT_KEY = os.environ.get("ARKHAM_WEBAPP_CLIENT_KEY", "gh67j345kl6hj5k432")


class ArkhamSDK:
    def __init__(
        self,
        base_url: str = ARKHAM_API_BASE,
        webapp_client_key: str = ARKHAM_WEBAPP_CLIENT_KEY,
        timeout: int = 100,
    ):
        self.base_url = base_url
        self.webapp_client_key = webapp_client_key
        self.timeout = timeout

    def build_headers(self, url: str) -> dict[str, str]:
        """构造 Arkham 未登录查询所需签名头。"""
        timestamp = str(int(time.time()))
        path = urlparse(url).path
        first_hash = hashlib.sha256(
            f"{path}:{timestamp}:{self.webapp_client_key}".encode()
        ).hexdigest()
        payload = hashlib.sha256(
            f"{self.webapp_client_key}:{first_hash}".encode()
        ).hexdigest()
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "origin": "https://intel.arkm.com",
            "referer": "https://intel.arkm.com/",
            "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
            ),
            "x-timestamp": timestamp,
            "x-payload": payload,
        }

    def query(self, address: str) -> list[dict[str, Any]]:
        """查询 Arkham 获取地址标签（无需登录）。"""
        if not self.webapp_client_key:
            return [{"error": "ARKHAM_WEBAPP_CLIENT_KEY 未配置"}]

        url = f"{self.base_url}/intelligence/address/{address}"
        headers = self.build_headers(url)
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException as exc:
            return [{"error": str(exc)}]

        if resp.status_code != 200:
            try:
                message = resp.json().get("message", resp.text)
            except ValueError:
                message = resp.text
            return [{"error": f"HTTP {resp.status_code}: {str(message)[:200]}"}]

        try:
            data = resp.json()
        except ValueError as exc:
            return [{"error": f"解析响应失败: {exc}"}]

        entity_name = (data.get("arkhamEntity") or {}).get("name")
        label_name = (data.get("arkhamLabel") or {}).get("name")

        tags = []
        if entity_name:
            tags.append(f"Entity: {entity_name}")
        if label_name:
            tags.append(f"Label: {label_name}")

        if not tags:
            return []
        return [{"chain": "Arkham", "tags": tags}]


_default_arkham_sdk = ArkhamSDK()


def query_arkham(address: str) -> list[dict[str, Any]]:
    """函数风格入口，便于与现有调用兼容。"""
    return _default_arkham_sdk.query(address)
