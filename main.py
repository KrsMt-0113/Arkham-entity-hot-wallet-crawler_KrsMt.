# version 1.0

import csv
import json
import time
import undetected_chromedriver as uc
import platform
import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains


def clear_console():
    if platform.system() == 'Windows':
        os.system('cls')  # Windows
    else:
        os.system('clear')  # macOS / Linux
    title = "=== Arkham Entity Hot Wallet Crawler @ KrsMt. ==="
    print(title)

clear_console()

Chain = [
    'bitcoin',
    'ethereum',
    'solana',
    'tron',
    'bsc',
    'arbitrum_one',
    'ton',
    'polygon',
    'dogecoin',
    'base',
    'sonic',
    'optimism',
    'mantle',
    'avalanche',
    'linea',
    'blast',
    'manta',
    'flare'
]
wallets = {}

def auto_login(driver):
    # 读取账号密码
    with open("account.txt", "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        if len(lines) < 2:
            print("account.txt 格式错误，应为两行：邮箱 + 密码")
            return False
        email, password = lines[0], lines[1]

    print("正在自动登录 Arkham...")

    driver.get("https://auth.arkm.com/login")
    time.sleep(2)

    try:
        email_input = driver.find_element("name", "email")
        password_input = driver.find_element("name", "password")
        login_button = driver.find_element("xpath", '//button[@type="submit"]')

        email_input.send_keys(email)
        password_input.send_keys(password)
        input("完成认证登录后继续...")
        print("正在登录...")

        driver.get("https://intel.arkm.com")
        time.sleep(5)
        login_link = driver.find_element("link text", "Login")
        login_link.click()
        time.sleep(5)

        print("登录完成。")
        clear_console()
        return True

    except Exception as e:
        print(f"自动登录失败：{e}")
        return False

def fetch_json_with_selenium(driver, api_url):
    print(f"正在获取数据...")
    driver.get(api_url)
    time.sleep(2)

    try:
        pre_element = driver.find_element("tag name", "pre")
        json_text = pre_element.text
        data = json.loads(json_text)

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("数据提取完毕。\n")
        return data

    except Exception as e:
        print(f"获取 JSON 失败: {e}")
        return None

def extract_hot_wallet(addr_info):
    if (
        addr_info.get('arkhamEntity', {}).get('name') == Entity and
        addr_info.get('arkhamLabel', {}).get('name') == 'Hot Wallet'
    ):
        address = addr_info['address']
        chain = addr_info.get('chain')
        label = addr_info['arkhamLabel']['name']
        arkm_url = f"https://intel.arkm.com/{address}"

        key = f"{address}@{chain}"
        wallets[key] = {
            'chain': chain,
            'address': address,
            'arkm_url': arkm_url,
            'label': label
        }

if __name__ == "__main__":
    will_continue = True
    options = uc.ChromeOptions()
    driver = uc.Chrome(headless=False)
    if not auto_login(driver):
        input("自动登录失败，请手动登录后按任意键继续:")
    while will_continue:
        Entity = input("请输入 Entity 名称：")
        entity = input("请输入 entity 字符串：")
        num = input("请输入提取的 transfer 数量（如 100）：")
        #profile_name = "SeleniumProfile"
        #options.add_argument(f"--user-data-dir={user_data_dir}")
        #options.add_argument(f"--profile-directory={profile_name}")
        for chain in Chain:
            url = f'https://api.arkm.com/transfers?base={entity}&flow=out&usdGte=1&sortKey=time&sortDir=desc&limit={num}&offset=0&tokens=&chains={chain}'
            print(f"正在读取实体{Entity}的{chain}链热钱包信息...")
            driver.get(url)
            data = fetch_json_with_selenium(driver, url)
            if data.get('transfers') is not None:
                for tx in data['transfers']:
                    extract_hot_wallet(tx.get('fromAddress', {}))

        result = list(wallets.values())

        with open(f"{Entity}.csv", mode="w", encoding="utf-8", newline="") as file:
            fieldnames = ['chain', 'address', 'arkm_url', 'label']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result)
            print(f"结果已保存为{Entity}.csv")

        while True:
            will_continue_input = input("是否继续获取数据？(y/n)")
            if will_continue_input == 'y':
                break
            elif will_continue_input == 'n':
                will_continue = False
                exit()
            else:
                print("无效输入。\n")