import requests
import json

from datetime import datetime

class APaaSClient:

    def __init__(self):
        pass

    def make_request(self, url, payload, headers):
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            print(e)
            return None
        return response

    def new_root(self, root_token, user_id):
        url = "https://apaas/apaas/backend/definesys/define-operations/xdap-app/event/v2/trigger/external?eventId=6736e1ef3a8e737f26353cb2&tenantId=241251302414221313"
        payload = json.dumps({
            "token": root_token,
            "user_id": user_id
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = self.make_request(url, payload, headers)
        #print(response.text)

    def new_document(self, name, parent_token, token, type, url, full_path, created_time, modified_time):
        url = "https://apaas/apaas/backend/definesys/define-operations/xdap-app/event/v2/trigger/external?eventId=6736e6cb3a8e737f26353cbc&tenantId=241251302414221313"

        # payload = json.dumps({
        #     "created_time": "2024-12-12 11:14:11",
        #     "modified_time": "2024-12-12 11:14:11",
        #     "name": "2024年2月26日 BP运营管理会议纪要",
        #     "parent_token": "nodcnwNuKn2Uaj8BrXRzvYNKRnh",
        #     "token": "HAPedGmOso4C7Ax97luclC6Lnbh",
        #     "type": "docx",
        #     "url": "https://definesys.feishu.cn/docx/HAPedGmOso4C7Ax97luclC6Lnbh",
        #     "full_path": ""
        # })
        payload = json.dumps({
            "created_time": created_time,
            "modified_time": modified_time,
            "name": name,
            "parent_token": parent_token,
            "token": token,
            "type": type,
            "url": url,
            "full_path": full_path
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = self.make_request(url, payload, headers)

        print(response.text)

    def new_bitables(self, name, token, type, url_income, full_path, created_time, modified_time):
        url = "https://apaas/apaas/backend/definesys/define-operations/xdap-app/event/v2/trigger/external?eventId=673c39f33535471443f5c8bc&tenantId=241251302414221313"
        payload = json.dumps({
            "name": name,
            "token": token,
            "type": type,
            "path": full_path,
            "url": url_income,
            "created_time": self.get_time(created_time),
            "modified_time": self.get_time(modified_time)
        })
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            requests.request("POST", url, headers=headers, data=payload)
        except Exception as e:
            return None

        #print(response.text)

    def get_time(self, timestamp) -> str:
        """
            将时间戳转换为日期对象，支持秒级和毫秒级时间戳。
            :param ts: 时间戳
            :return: 返回格式为：%Y-%m-%d %H:%M:%S 的日期
            """
        try:
            ts = int(timestamp)
        except ValueError:
            return "时间戳输入错误，请检查后重试！"

        if len(str(ts)) == 10:
            date_obj = datetime.fromtimestamp(ts)
        elif len(str(ts)) == 13:
            date_obj = datetime.fromtimestamp(ts / 1000)
        else:
            return "时间戳输入错误，请检查后重试！"

        return date_obj.strftime("%Y-%m-%d %H:%M:%S")