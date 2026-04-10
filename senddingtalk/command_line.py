# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import python_atom_sdk as sdk
from .error_code import ErrorCode
import json
import requests
import time
import hmac
import hashlib
import base64
try:
    import urllib.parse as urllib
except ImportError:
    import urllib


err_code = ErrorCode()


def exit_with_error(error_type=None, error_code=None, error_msg="failed"):
    """
    @summary: exit with error
    """
    if not error_type:
        error_type = sdk.OutputErrorType.PLUGIN
    if not error_code:
        error_code = err_code.PLUGIN_ERROR
    sdk.log.error("error_type: {}, error_code: {}, error_msg: {}".format(error_type, error_code, error_msg))

    output_data = {
        "status": sdk.status.FAILURE,
        "errorType": error_type,
        "errorCode": error_code,
        "message": error_msg,
        "type": sdk.output_template_type.DEFAULT
    }
    sdk.set_output(output_data)

    exit(error_code)


def exit_with_succ(data=None, quality_data=None, msg="run succ"):
    """
    @summary: exit with succ
    """
    if not data:
        data = {}

    output_template = sdk.output_template_type.DEFAULT
    if quality_data:
        output_template = sdk.output_template_type.QUALITY

    output_data = {
        "status": sdk.status.SUCCESS,
        "message": msg,
        "type": output_template,
        "data": data
    }

    if quality_data:
        output_data["qualityData"] = quality_data

    sdk.set_output(output_data)

    sdk.log.info("finish")
    exit(err_code.OK)


def get_user_info(app_code, app_token, username, url):
    params = {
        "bk_app_code": app_code,
        "bk_app_secret": app_token,
        "bk_username": "admin",
        "exact_lookups": username
    }
    sdk.log.info("params is {}".format(params))
    api_url = url + "/api/c/compapi/v2/usermanage/list_users/"
    sdk.log.info("api_url is {}".format(api_url))
    headers = {'Content-Type': 'application/json;charset=utf-8'}
    resp = requests.get(
        url=api_url, headers=headers, params=params
    )
    sdk.log.info("res is {}".format(resp.content))
    res = resp.json()
    sdk.log.info("res is {}".format(res))
    ddNumber = res["data"]["results"][0]["extras"]["ddNumber"]
    return ddNumber


class SendDingTalk(object):

    def __init__(self, sign):
        self.sign = sign

    def exec_sign(self):
        timestamp = str(int(time.time() * 1000))
        secret = self.sign
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def send(self, content, token, type, dest_users=[], title="", send_all=False):
        timestamp, sign = self.exec_sign()
        url = "https://oapi.dingtalk.com/robot/send?access_token={}&timestamp={}&sign={}".format(token, timestamp,
                                                                                                 sign)
        json_text = {
            "text": {
                "content": content
            },
            "msgtype": "text",
            "at": {
                "isAtAll": send_all,
                "atDingtalkIds": dest_users
            }
        }
        if type == "markdown":
            for user in dest_users:
                if dest_users.index(user) == 0:
                    content += "\n" + "@" + user
                else:
                    content += "@" + user
            if send_all:
                content += "\n" + "@all"
            json_text = {
                "msgtype": type,
                "markdown": {
                    "title": title,
                    "text": content
                },
                "at": {
                    "isAtAll": send_all,
                    "atDingtalkIds": dest_users
                }
            }
        sdk.log.info("json_text is {}".format(json_text))
        self.post_req(url, json_text)

    @staticmethod
    def post_req(url, json_text):
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        resp = requests.post(url, json.dumps(json_text), headers=headers)
        if resp.status_code != 200:
            exit_with_error(error_type=sdk.output_error_type.THIRD_PARTY,
                            error_code=err_code.THIRD_SYSTEM_ERROR,
                            error_msg=resp.text)
        res = resp.json()
        if res.get('errcode') != 0:
            exit_with_error(error_type=sdk.output_error_type.THIRD_PARTY,
                            error_code=err_code.THIRD_SYSTEM_ERROR,
                            error_msg=res.get("errmsg"))
        return resp


def main():
    """
    @summary: main
    """
    sdk.log.info("enter main")

    # 输入
    input_params = sdk.get_input()

    # 获取名为input_demo的输入字段值
    sign = input_params.get("sign", None)
    sdk.log.info("sign is {}".format(sign))
    if not sign:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="sign is None")
    token = input_params.get("webhook", None)
    sdk.log.info("webhook is {}".format(token))
    if not token:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="webhook is None")
    msgtype = input_params.get("msgtype", None)
    sdk.log.info("msgtype is {}".format(msgtype))
    if not msgtype:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="msgtype is None")
    content = input_params.get("t_content") if msgtype == "text" else input_params.get("m_content")
    if not content:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="content is None")
    start_user_name = input_params.get("start_user_name", None)
    usernames = input_params.get("usernames", None)
    sdk.log.info("start_user_name is {}".format(start_user_name))
    sdk.log.info("usernames is {}".format(usernames))
    title = input_params.get("title", "")
    app_code = sdk.get_sensitive_conf("app_code")
    app_token = sdk.get_sensitive_conf("app_token")
    bk_paas_host = sdk.get_sensitive_conf("bk_paas_host")

    # sign = sdk.get_sensitive_conf("sign")

    if not app_code:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="app_code is None")
    if not app_token:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="app_token is None")
    # if not sign:
    #     exit_with_error(error_type=sdk.output_error_type.USER,
    #                     error_code=err_code.USER_CONFIG_ERROR,
    #                     error_msg="sign is None")
    if not bk_paas_host:
        exit_with_error(error_type=sdk.output_error_type.USER,
                        error_code=err_code.USER_CONFIG_ERROR,
                        error_msg="bk_paas_host is None")

    # 插件逻辑
    try:
        import sys
        reload(sys)
        sys.setdefaultencoding('utf8')
    except NameError:
        pass
    send_all = False
    dest_users = []
    user_list = []
    if start_user_name == "true":
        start_user = sdk.get_pipeline_start_user_name()
        user_list.append(start_user)
    if usernames:
        usernames = json.loads(usernames)
        # if len(usernames) == 1 and "," in usernames[0]:
        #     user_list += usernames[0].split(",")
        # else:
        #     user_list += usernames

        for item in usernames:
            if "," in item:
                user_list += item.split(",")
            else:
                user_list.append(item)
    user_list = list(set(user_list))
    if "@all" in user_list:
        send_all = True
    else:
        for user in user_list:
            ddNumber = get_user_info(app_code, app_token, user, bk_paas_host)
            dest_users.append(ddNumber)
    sdk.log.info("dest_users is {}".format(dest_users))
    send_dd = SendDingTalk(sign)
    send_dd.send(content, token, msgtype, dest_users=dest_users, title=title, send_all=send_all)

    # 插件执行结果、输出数据
    data = {
        "output_demo": {
            "type": sdk.output_field_type.STRING,
            "value": "test output"
        }
    }
    exit_with_succ(data=data)

    exit(0)
