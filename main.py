# 2025.8.10
# version: 4.0
# 使用 ArkhamSDK 签名头访问 https://api.arkm.com，无需 API-Key

import time
import requests
import csv

import sys
import os
import builtins
from datetime import datetime

from arkham_sdk import ArkhamSDK

original_print = print

def timestamped_print(*args, **kwargs):
    now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    original_print(now, *args, **kwargs)

builtins.print = timestamped_print

is_github = os.getenv("GITHUB_ACTIONS") == "true"

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.abspath(".")

# 全局 SDK 实例，用于生成签名头
arkham_sdk = ArkhamSDK()


def extract_hot_wallet(addr_info, target, name):
    if (
        addr_info.get('arkhamEntity', {}).get('name') == name
        # addr_info.get('arkhamEntity', {}).get('name') == name and
        # addr_info.get('arkhamLabel', {}).get('name') == 'Hot Wallet'
    ):
        address = addr_info['address']
        chain = addr_info.get('chain')
        label = addr_info.get('arkhamLabel', {}).get('name')
        arkm_url = f"https://intel.arkm.com/explorer/address/{address}"

        key = f"{address}@{chain}"
        target[key] = {
            'chain': chain,
            'address': address,
            'arkm_url': arkm_url,
            'label': label
        }


def fetch_chain_data(chain, entity, num, Entity, offset_limit):
    """单链顺序拉取 transfers，使用 Arkham 签名头。"""
    merged_result = {}
    limit = num
    try:
        for i in range(offset_limit):
            offset = i * limit
            time.sleep(1)
            url = f"{arkham_sdk.base_url}/transfers"
            querystring = {
                "base": entity,
                "chains": chain,
                "flow": "out",
                "limit": limit,
                "offset": offset,
                "sortKey": "time",
                "sortDir": "desc",
                "usdGte": 1,
            }
            headers = arkham_sdk.build_headers(url)
            response = requests.get(
                url,
                headers=headers,
                params=querystring,
                timeout=arkham_sdk.timeout,
            )
            if response.status_code != 200:
                print(f"[{Entity}] {chain} HTTP {response.status_code}: {response.text[:200]}")
                # 4xx 视为永久失败，跳过该链；5xx 视为可重试
                if 400 <= response.status_code < 500:
                    return chain, merged_result
                return chain, None
            transfers = response.json().get('transfers')
            if not transfers:
                break
            for tx in transfers:
                if tx.get('fromAddressOwner'):
                    extract_hot_wallet(tx.get('fromAddressOwner', {}), merged_result, Entity)
                else:
                    extract_hot_wallet(tx.get('fromAddress', {}), merged_result, Entity)
        return chain, merged_result
    except Exception as e:
        print(f"[{Entity}] {chain} Failed：{e}")
        return chain, None


if __name__ == "__main__":
    print("Arkm Entity Hot Wallet Crawler @ KrsMt.")
    print("process start")

    # 查询参数固定为 3000 * 5
    num = 1000
    offset_limit = 10

    Chain = [
        'bitcoin',
        # 'ethereum',
        # 'solana',
        # 'tron',
        # 'dogecoin',
        # 'ton',
        # 'base',
        # 'arbitrum_one',
        # 'sonic',
        # 'optimism',
        # 'mantle',
        # 'avalanche',
        # 'bsc',
        # 'linea',
        # 'polygon',
        # 'blast',
        # 'manta',
        # 'flare'
    ]

    args_path = os.path.join(base_path, "args.txt")
    if not os.path.exists(args_path):
        print("[wrong] can't find 'args.txt' (see README.md)")
        sys.exit(1)

    with open(args_path, "r", encoding="utf-8") as arg_file:
        lines = [line.strip() for line in arg_file if line.strip()]

    def process_entity(line, position):
        Entity, entity = [x.strip() for x in line.split(',', 1)]

        result = {}
        # 单线程顺序遍历每条链，失败则重试
        for chain in Chain:
            while True:
                ch, partial = fetch_chain_data(chain, entity, num, Entity, offset_limit)
                if partial is None:
                    print(f"[{Entity}] {ch} retry...")
                    continue
                result.update(partial)
                print(f"[{Entity}] {ch} chain {len(partial)} hot wallets found.")
                break

        result = [result[key] for chain in Chain for key in result if result[key]['chain'] == chain]

        os.makedirs(os.path.join(base_path, "result"), exist_ok=True)
        file2_path = os.path.join(base_path, "result", f"{Entity}.csv")

        with open(file2_path, mode="w", encoding="utf-8", newline="") as file:
            fieldnames = ['chain', 'address', 'arkm_url', 'label']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result)

    for i, line in enumerate(lines):
        process_entity(line, i)

    sys.exit()
