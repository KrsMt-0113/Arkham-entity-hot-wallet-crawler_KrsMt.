# 2025.7.24
# version: 3.0
# 自行获取cURL存入curl.txt即可。

import re
import time
import requests
import csv

import sys
import os
import concurrent.futures
import builtins
from datetime import datetime

original_print = print

def timestamped_print(*args, **kwargs):
    now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    original_print(now, *args, **kwargs)

# 替换全局 print
builtins.print = timestamped_print

is_github = os.getenv("GITHUB_ACTIONS") == "true"

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.abspath(".")



def clear_console():
    # if platform.system() == 'Windows':
    #     os.system('cls')  # Windows
    # else:
    #     os.system('clear')  # macOS / Linux
    title = "========= Arkham Entity Hot Wallet Crawler @ KrsMt. ========="
    print(title)

def parse_curl(curl_text):
    headers = dict(re.findall(r"-H\s+'([^:]+):\s*(.*?)'", curl_text))

    cookie_match = re.search(r"-b\s+'([^']+)'", curl_text)
    cookie_str = cookie_match.group(1) if cookie_match else headers.pop('cookie', headers.pop('Cookie', ''))

    cookies = {}
    if cookie_str:
        for pair in cookie_str.split('; '):
            if '=' in pair:
                k, v = pair.split('=', 1)
                cookies[k] = v

    return headers, cookies

def extract_hot_wallet(addr_info, target, name):
    if (
        addr_info.get('arkhamEntity', {}).get('name') == name and
        addr_info.get('arkhamLabel', {}).get('name') == 'Hot Wallet'
    ):
        address = addr_info['address']
        chain = addr_info.get('chain')
        label = addr_info['arkhamLabel']['name']
        arkm_url = f"https://intel.arkm.com/explorer/address/{address}"

        key = f"{address}@{chain}"
        target[key] = {
            'chain': chain,
            'address': address,
            'arkm_url': arkm_url,
            'label': label
        }

def fetch_chain_data(chain, entity, num, headers, cookies, Entity, offset_limit):
    merged_result = {}
    limit = num
    try:
        for i in range(offset_limit):
            offset = i * limit
            time.sleep(1)
            url = f'https://api.arkm.com/transfers?base={entity}&flow=out&usdGte=1&sortKey=time&sortDir=desc&limit={limit}&offset={offset}&tokens=&chains={chain}'
            response = requests.get(url, headers=headers, cookies=cookies, timeout=20)
            transfers = response.json().get('transfers')
            if not transfers:
                break
            for tx in transfers:
                extract_hot_wallet(tx.get('fromAddress', {}), merged_result, Entity)
        return chain, merged_result
    except Exception as e:
        print(f"[{Entity}] {chain} 链出错：{e}")
        return chain, None


if __name__ == "__main__":
    print("✅ Arkham 热钱包爬虫程序开始运行")
    # print("\033]0;Arkham Hot Wallet Crawler @ KrsMt.\007")
    file1_path = os.path.join(base_path, "curl.txt")

    config_path = os.path.join(base_path, "config.txt")
    num = 1000
    offset_limit = 3

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("num="):
                    try:
                        num = int(line.split("=", 1)[1])
                    except:
                        pass
                elif line.startswith("offset="):
                    try:
                        offset_limit = int(line.split("=", 1)[1])
                    except:
                        pass

    Chain = [
        'bitcoin',
        'ethereum',
        'solana',
        'tron',
        'dogecoin',
        'ton',
        'base',
        'arbitrum_one',
        'sonic',
        'optimism',
        'mantle',
        'avalanche',
        'bsc',
        'linea',
        'polygon',
        'blast',
        'manta',
        'flare'
    ]

    with open(file1_path, "r", encoding="utf-8") as f:
        curl_text = f.read()

    headers, cookies = parse_curl(curl_text)
    # clear_console()

    args_path = os.path.join(base_path, "args.txt")
    if not os.path.exists(args_path):
        print("❌ 缺少 args.txt 文件，请在同目录下提供，格式为每行一个 Entity,entity")
        sys.exit(1)

    with open(args_path, "r", encoding="utf-8") as arg_file:
        lines = [line.strip() for line in arg_file if line.strip()]

    num_chains = len(Chain)

    def process_entity(line, position):
        if ',' not in line:
            print(f"❌ 格式错误：{line}")
            return
        Entity, entity = [x.strip() for x in line.split(',', 1)]

        result = {}
        # Track which chains have completed successfully
        completed_chains = set()
        # Use a thread pool for all chains, keep retrying failed chains immediately
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Map: future -> chain
            future_to_chain = {
                executor.submit(fetch_chain_data, chain, entity, num, headers, cookies, Entity, offset_limit): chain
                for chain in Chain
            }
            while future_to_chain:
                # Wait for any future to complete
                done, _ = concurrent.futures.wait(future_to_chain, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    chain = future_to_chain.pop(future)
                    ch, partial = future.result()
                    if partial is None:
                        # Resubmit this chain immediately
                        new_future = executor.submit(fetch_chain_data, ch, entity, num, headers, cookies, Entity, offset_limit)
                        future_to_chain[new_future] = ch
                    else:
                        result.update(partial)
                        completed_chains.add(ch)
                        print(f"[{Entity}] {ch} 链共找到 {len(partial)} 个热钱包。")

        # 按 Chain 顺序排序
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
