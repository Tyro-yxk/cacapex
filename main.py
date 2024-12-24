import json
import os
import re

import requests
from requests import Timeout


# 联通性测试
def connectivity_test(timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        print(f"Website {url} is reachable with status code {response.status_code}")
    except Timeout:
        print(f"Connection to website {url} timed out after {timeout} seconds")
        exit(-1)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        exit(-1)


def login(_email, _password, _headers=None) -> tuple[str, str]:
    _token = None
    _authorization = None
    login_data = {
        "email": _email,
        "password": _password
    }
    r = requests.post(url + "/passport/auth/login", data=login_data, headers=_headers)
    if r.status_code == 200:
        _token = r.json()["data"]["token"]
        _authorization = r.json()["data"]["auth_data"]
    return _token, _authorization


def get_fetch_list() -> str:
    _free_id = None
    response = requests.get(url + f"/user/plan/fetch?t={token}", headers=headers)
    if response.status_code == 200:
        for plan in response.json()["data"]:
            if plan["name"] == "免费套餐":
                _free_id = plan["id"]
    return _free_id


def free_fetch():
    _exchange_id = None
    response = requests.get(url + f"/user/plan/fetch?t={token}&id={free_id}", headers=headers)
    if response.status_code == 200:
        feature = (json.loads(response.json()["data"]["content"]))[-1]["feature"]
        pattern = r'[a-zA-Z0-9]{3,}'
        match = re.search(pattern, feature)
        if match:
            _exchange_id = match.group()
    return _exchange_id


def check_fetch() -> str:
    data = {
        "code": exchange_id,
        "plan_id": free_id
    }
    _limit_period = None
    response = requests.post(url + "/user/coupon/check", data=data, headers=headers)
    if response.status_code == 200:
        _limit_period = response.json()["data"]["limit_period"][0]
    return _limit_period


def create_order() -> str:
    data = {
        "plan_id": free_id,
        "period": limit_period,
        "coupon_code": exchange_id
    }
    response = requests.post(url + "/user/order/save", data=data, headers=headers)
    _order_id = None
    if response.status_code == 200:
        _order_id = response.json()["data"]
    return _order_id


# 支付订单
def pay_order():
    _pay = False
    data = {
        "trade_no": order_id,
        "method": 1
    }
    response = requests.post(url + "/user/order/checkout", data=data, headers=headers)
    if response.status_code == 200:
        print(response.json(), "\n支付成功")
        _pay = True
    else:
        print(response.json())
    return _pay


user_list = os.environ["USER_LIST"].strip().split(";")

# 登录 获取token
url = "https://cacapex.com"

useragent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 "
             "Safari/537.36 Edg/131.0.0.0")
user = []

for i, u_list in enumerate(user_list):
    email = u_list.split(",")[0]
    password = u_list.split(",")[1]
    user.append({"email": email, "password": password})

connectivity_test()
url = url + "/api/v1"
for user in user:
    # 登录
    token, authorization = login(user["email"], user["password"], {"User-Agent": useragent})
    if token is None or authorization is None:
        print("登录失败")
        continue
    headers = {"User-Agent": useragent, "Authorization": authorization}
    # 获取订阅列表中的免费订阅id
    free_id = get_fetch_list()
    if free_id is None:
        print("获取免费ID失败")
        continue
    # 从详情总获取兑换码
    exchange_id = free_fetch()
    if exchange_id is None:
        print("兑换码获取失败")
        continue
    # 验证兑换码
    limit_period = check_fetch()
    if limit_period is None:
        print("兑换码检验失败")
        continue
    # 生成订单
    order_id = create_order()
    if order_id is None:
        print("订单创建失败")
        continue
    # 支付
    pay = pay_order()
    if not pay:
        print("支付失败")
        continue
