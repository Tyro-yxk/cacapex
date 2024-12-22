import json
import os
import re

import requests
from requests import Timeout


# 联通性测试
def connectivity_test(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        print(f"Website {url} is reachable with status code {response.status_code}")
    except Timeout:
        print(f"Connection to website {url} timed out after {timeout} seconds")
        exit(-1)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        exit(-1)


def login(url, email, password, headers=None) -> tuple[str, str]:
    token = None
    authorization = None
    login_data = {
        "email": email,
        "password": password
    }
    r = requests.post(url, data=login_data, headers=headers)
    if r.status_code == 200:
        token = r.json()["data"]["token"]
        authorization = r.json()["data"]["auth_data"]
    return token, authorization


def get_fetch_list(url, headers=None) -> str:
    free_id = None
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        for plan in response.json()["data"]:
            if plan["name"] == "免费套餐":
                free_id = plan["id"]
    return free_id


def free_fetch(url, headers=None):
    exchange_id = None
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        feature = (json.loads(response.json()["data"]["content"]))[-1]["feature"]
        pattern = r'[a-zA-Z0-9]{3,}'
        match = re.search(pattern, feature)
        if match:
            exchange_id = match.group()
    return exchange_id


def check_fetch(url, exchange_id, free_id, headers=None):
    data = {
        "code": exchange_id,
        "plan_id": free_id
    }
    limit_period = None
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        limit_period = response.json()["data"]["limit_period"][0]
    return limit_period


def create_order(url, free_id, limit_period, exchange_id, headers=None) -> str:
    data = {
        "plan_id": free_id,
        "period": limit_period,
        "coupon_code": exchange_id
    }
    response = requests.post(url, data=data, headers=headers)
    order_id = None
    if response.status_code == 200:
        order_id = response.json()["data"]
    return order_id


# 支付订单
def pay_order(url, order_id, headers=None):
    pay = False
    data = {
        "trade_no": order_id,
        "method": 1
    }
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        print(response.json(), "\n支付成功")
        pay = True
    else:
        print(response.json())
    return pay


user_list = os.environ["USER_LIST"].strip().split(";")

# 登录 获取token
url = "https://cacapex.com"

useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
user = []

for i, u_list in enumerate(user_list):
    email = u_list.split(",")[0]
    password = u_list.split(",")[1]
    user.append({"email": email, "password": password})

connectivity_test(url)
url = url + "/api/v1"
for user in user:
    # 登录
    url_login = url + "/passport/auth/login"
    token, authorization = login(url_login, user["email"], user["password"], {"User-Agent": useragent})
    if token is None or authorization is None:
        print("登录失败")
        continue
    headers = {"User-Agent": useragent, "Authorization": authorization}
    # 获取订阅列表中的免费订阅id
    fetch_url = url + "/user/plan/fetch?t={}".format(token)
    free_id = get_fetch_list(fetch_url, headers)
    if free_id is None:
        print("获取免费ID失败")
        continue
    # 从详情总获取兑换码
    fetch_free_url = fetch_url + "&id={}".format(free_id)
    exchange_id = free_fetch(fetch_free_url, headers)
    if exchange_id is None:
        print("兑换码获取失败")
        continue
    # 验证兑换码
    check_url = url + "/user/coupon/check"
    limit_period = check_fetch(check_url, exchange_id, free_id, headers)
    if limit_period is None:
        print("兑换码检验失败")
        continue
    # 生成订单
    save_url = url + "/user/order/save"
    order_id = create_order(save_url, free_id, limit_period, exchange_id, headers)
    if order_id is None:
        print("订单创建失败")
        continue
    # 支付
    checkout_url = url + "/user/order/checkout"
    pay = pay_order(checkout_url, order_id, headers)
    if not pay:
        print("支付失败")
        continue
