import json

import lark_oapi as lark
lark.logger.setLevel(lark.LogLevel.INFO.name)

import requests
from lark_oapi.api.auth.v3 import *
from lark_oapi.api.drive.v1 import ListFileRequest, ListFileResponse, ListFileResponseBody, DownloadFileRequest, \
    DownloadFileResponse, CreateExportTaskRequest, ExportTask, CreateExportTaskResponse, GetExportTaskRequest, \
    GetExportTaskResponse, GetExportTaskResponseBody, DownloadExportTaskRequest, DownloadExportTaskResponse, \
    ListFileRequestBuilder
from lark_oapi.api.wiki.v2 import ListSpaceRequest, ListSpaceResponse, ListSpaceResponseBody, Space, GetSpaceRequest, \
    GetSpaceResponse, ListSpaceNodeRequest, ListSpaceNodeResponse


class FeishuDriveClient:
    """
    完成飞书基础API的封装即可，不直接处理同步逻辑.
    主要用于同步飞书云空间（飞书云盘）
    """
    # client = None
    user_access_token: str = None
    root_doc_token: str = None
    root_doc_user_id: str = None

    # def __init__(self, app_id, app_secret):
    #     self.app_id = app_id
    #     self.app_secret = app_secret
    def __init__(self, user_access_token, cookies):
        self.user_access_token = user_access_token
        self.cookies = cookies

    # 通常是2H（7200s）的生命周期，应该够用了
    def user_access_mode(self, user_access_token):
        self.user_access_token = user_access_token
        lark.logger.debug("user_access_mode enabled, user_access_token: " + user_access_token)

    def get_client(self) -> lark.Client:
        c: lark.Client = lark.Client.builder() \
            .enable_set_token(True) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        return c

    # def get_app_access_token(self):
    #     request: InternalAppAccessTokenRequest = InternalAppAccessTokenRequest.builder() \
    #         .request_body(InternalAppAccessTokenRequestBody.builder()
    #                       .app_id(self.app_id)
    #                       .app_secret(self.app_secret)
    #                       .build()) \
    #         .build()
    #
    #     # 发起请求
    #     response: InternalAppAccessTokenResponse = self.get_client().auth.v3.app_access_token.internal(request)
    #
    #     # 处理失败返回
    #     if not response.success():
    #         lark.logger.error(
    #             f"client.auth.v3.app_access_token.internal failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
    #         return
    #
    #     #json_response = lark.JSON.marshal(response)
    #     json_response = json.loads(response.raw.content)
    #     #lark.logger.info(json_response)
    #     #示例值 {'app_access_token': 't-g104bfam3MEOTTQEHAO3LGQVQ7ZWMA2D73YSH5HQ', 'code': 0, 'expire': 4099, 'msg': 'ok', 'tenant_access_token': 't-g104bfam3MEOTTQEHAO3LGQVQ7ZWMA2D73YSH5HQ'}
    #     #print(json_response['app_access_token'])
    #     return json_response['app_access_token']

    def get_user_access_token(self):
        return self.user_access_token

    def load_root_list(self):
        url = "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta"
        payload = {}
        headers = {
            'Authorization': f'Bearer {self.user_access_token}',
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        try:
            self.root_doc_token = response.json()['data']['token']
            self.root_doc_user_id = response.json()['data']['user_id']
            return response.json()
        except:
            raise Exception("User access token failed, Please refresh")

        # print(response.json())
    def load_shared_list(self):
        import requests

        url = "https://definesys.feishu.cn/space/api/explorer/v2/share/folder/list/?asc=0&rank=5&hidden=0&length=200"

        payload = {}
        headers = {
            'accept': 'application/json, text/plain, */*',
            'cookie': self.cookies,
            'referer': 'https://definesys.feishu.cn/drive/shared/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        try:
            result = json.loads(response.text)
            # print(result)
            nodes_list = result['data']['node_list']
            nodes_entities = result['data']["entities"]["nodes"]
            return nodes_list, nodes_entities
        except:
            raise Exception("User access token failed, Please refresh")

        #print(response.text)

    def get_files_list(self, folder_token, page_token, page_size: 200) -> ListFileResponseBody:
        """
        文档地址：
        https://open.feishu.cn/api-explorer/cli_a473cf4bdc71d00b?apiName=list&from=op_doc_tab&project=drive&resource=file&version=v1

        :param folder_token:
        :param page_token:
        :param page_size:
        :return:
        """
        rb: ListFileRequestBuilder = ListFileRequest.builder()
        if page_token is not None:
            rb.page_token(page_token)
        request: ListFileRequest = rb \
            .page_size(page_size) \
            .folder_token(folder_token) \
            .order_by("CreatedTime") \
            .direction("DESC") \
            .build()

        option = lark.RequestOption.builder().user_access_token(
            self.user_access_token).build()
        response: ListFileResponse = self.get_client().drive.v1.file.list(request, option)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.drive.v1.file.list failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        return response.data

    def download_file(self, file_token, file_path):
        """
        针对 type = file的文件
        :param file_token:
        :return:
        """
        #print(file_token)
        # 构造请求对象
        request: DownloadExportTaskRequest = DownloadExportTaskRequest.builder() \
            .file_token(file_token) \
            .build()

        # 发起请求
        option = lark.RequestOption.builder().user_access_token(
            self.user_access_token).build()
        response: DownloadExportTaskResponse = self.get_client().drive.v1.export_task.download(request, option)

        # 处理失败返回
        #print(lark.JSON.marshal(response))
        if not response.success():
            lark.logger.error(
                f"client.drive.v1.export_task.download failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n")
            return

        try:
            f = open(file_path, "wb")
            f.write(response.file.read())
            f.close()
            lark.logger.info(f"【下载成功】{file_path}")
            return
        except Exception as e:
            lark.logger.error(e)
            return

        #return response
        # 处理业务结果，返回流后再做处理。


    # def download_document(self, file_token):
    #     """
    #     针对 type 不是 file 的文件
    #     需要经历三个步骤
    #     1. 创建导出任务；
    #     2. 查询导出任务结果；
    #     3. 下载导出文件。
    #     :param file_token:
    #     :return:
    #     """
    #     return

    def download_document_buy_ticket(self, doc_token, doc_type, file_extension) -> str:
        """
        频率限制 100 次/分钟
        :param file_token:
        :param doc_type:
        :param file_extension:
        :return: 获得一个文件同步的ticket
        """
        request: CreateExportTaskRequest = CreateExportTaskRequest.builder() \
            .request_body(ExportTask.builder()
                          .file_extension(file_extension)
                          .token(doc_token)
                          .type(doc_type)
                          .build()) \
            .build()

        # 发起请求
        option = lark.RequestOption.builder().user_access_token(
            self.user_access_token).build()
        response: CreateExportTaskResponse = self.get_client().drive.v1.export_task.create(request, option)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.drive.v1.export_task.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        #lark.logger.info(lark.JSON.marshal(response.data, indent=4))
        return response.data.ticket

    def download_document_check_ticket(self, ticket, doc_token) -> GetExportTaskResponse:
        """
        检查云上的在线文档导出任务完成情况，完成的话可以获得文件名、Size、file_token等信息
        :param ticket:
        :param file_token:
        :return: 返回一个可用于文件下载的file_token
        {
          "code": 0, # 错误码，非 0 表示失败
          "data": {
            "result": {
              "extra": {
                "is_complete": "true"
              },
              "file_extension": "docx",
              "file_name": "2024年2月26日 BP运营管理会议纪要",
              "file_size": 5145,
              "file_token": "HcCxb7HTCoPHx7x62EBcXRSznxf",
              "job_error_msg": "success",
              "job_status": 0,
              "type": "docx"
            }
          },
          "msg": "success"
        }
        """
        request: GetExportTaskRequest = GetExportTaskRequest.builder() \
            .ticket(ticket) \
            .token(doc_token) \
            .build()

        # 发起请求
        option = lark.RequestOption.builder().user_access_token(
            self.user_access_token).build()
        response: GetExportTaskResponse = self.get_client().drive.v1.export_task.get(request, option)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.drive.v1.export_task.get failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        #lark.logger.info(lark.JSON.marshal(response, indent=4))

        # 处理业务结果
        return response

    def download_document_get_file(self, file_token, file_path) :

        request: DownloadFileRequest = DownloadFileRequest.builder() \
            .file_token(file_token) \
            .build()

        # 发起请求
        option = lark.RequestOption.builder().user_access_token(
            self.user_access_token).build()
        response: DownloadFileResponse = self.get_client().drive.v1.file.download(request, option)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.drive.v1.file.download failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # # 处理业务结果
        f = open(f"{file_path}", "wb")
        f.write(response.file.read())
        f.close()

        # with open(file_path, 'wb') as f:
        #     for chunk in response.iter_content(chunk_size=1024):
        #         f.write(chunk)


class FeishuSpaceClient:
    client = None

    def __init__(self, user_access_token, cookies, csrf_token):
        self.user_access_token = user_access_token
        self.cookies = cookies
        self.csrf_token = csrf_token

    def get_client(self):
        c: lark.Client = lark.Client.builder() \
            .enable_set_token(True) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        self.client = c
        return c

    def get_option(self):
        option = lark.RequestOption.builder().user_access_token(
            self.user_access_token).build()
        return option

    def reset_token(self, user_access_token):
        self.user_access_token = user_access_token

    def set_csrf_token(self, csrf_token):
        self.csrf_token = csrf_token

    def get_spaces_list(self, page_token, page_size) -> ListSpaceResponseBody:
        if page_token:
            request: ListSpaceRequest = ListSpaceRequest.builder() \
                .page_size(page_size) \
                .page_token(page_token) \
                .build()
        else:
            request: ListSpaceRequest = ListSpaceRequest.builder() \
                .page_size(page_size) \
                .build()
        # 发起请求
        option = self.get_option()
        response: ListSpaceResponse = self.get_client().wiki.v2.space.list(request, option)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.wiki.v2.space.list failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        #lark.logger.info(lark.JSON.marshal(response.data, indent=4))
        return response.data

    def get_all_spaces_list(self, page_token, page_size) -> List[Space]:
        spaces_response = self.get_spaces_list(page_token, page_size)
        page_token = spaces_response.page_token
        spaces: List[Space] = spaces_response.items
        has_more = spaces_response.has_more
        while has_more and page_token:
            page_spaces_response = self.get_spaces_list(page_token, page_size)
            page_token = page_spaces_response.page_token
            has_more = page_spaces_response.has_more
            spaces.append(page_spaces_response.items)

        return spaces

    def get_files_list(self, space_node_id: str, parent_node_token: str, page_token: str):
        # 构造请求对象
        requester_builder = ListSpaceNodeRequest.builder()
        requester_builder.space_id(space_id=space_node_id)
        if parent_node_token:
            requester_builder.parent_node_token(parent_node_token)
        if page_token:
            requester_builder.page_token(page_token)
        request: ListSpaceNodeRequest =  requester_builder.build()

        # 发起请求
        response: ListSpaceNodeResponse = self.get_client().wiki.v2.space_node.list(request, self.get_option())
        #print(response)
        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.wiki.v2.space_node.list failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}")
            return

        return response.data

    def get_space_info(self, space_id) -> Space:
        request: GetSpaceRequest = GetSpaceRequest.builder() \
            .space_id(space_id) \
            .build()

        # 发起请求
        option = self.get_option()
        response: GetSpaceResponse = self.get_client().wiki.v2.space.get(request, option)

        # 处理失败返回
        if not response.success():
            lark.logger.error(
                f"client.wiki.v2.space.get failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
            return

        # 处理业务结果
        #lark.logger.info(lark.JSON.marshal(response.data, indent=4))
        """
        "space": {
            "name": "知识空间",
            "description": "知识空间描述",
            "space_id": "1565676577122621"
        }
        """
        return response.data.space

    def download_document_buy_ticket(self, node_token, obj_token, obj_type: str) -> str:
        url = f"https://definesys.feishu.cn/space/api/export/create/?synced_block_host_token={obj_token}&synced_block_host_type=22"

        payload = json.dumps({
            "token": obj_token,
            "type": obj_type,
            "file_extension": "docx",  # DOWNLOAD_AS
            "event_source": "6",
            "need_comment": False
        })

        headers = {
          'accept': 'application/json',
          'content-type': 'application/json',
          'cookie': self.cookies,
          'referer': f'https://definesys.feishu.cn/wiki/{node_token}?fromScene=spaceOverview',
          'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
          'x-csrftoken': self.csrf_token
        }
        #print(headers)
        response = requests.request("POST", url, headers=headers, data=payload)
        result = json.loads(response.text)
        #print(result)
        ticket = result.get("data").get("ticket")

        return ticket

    def download_document_check_ticket(self, ticket, node_token, obj_token, doc_type):
        if ticket is None:
            raise Exception("ticket is None")
        url = f"https://definesys.feishu.cn/space/api/export/result/{ticket}?token={obj_token}&type={doc_type}"
        #print(url)
        payload = {}
        headers = {
            'authority': 'definesys.feishu.cn',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh,en;q=0.9,zh-CN;q=0.8',
            # 'context':'request_id=cvSlaMhmHDzb-c938fb191e76a4c6da3038aaf9ac0894d214e948;os=mac;app_version=1.0.13.2383;os_version=10.15.7;platform=web' ,
            'cookie': self.cookies,
            'doc-biz': 'Lark',
            'doc-os': 'mac',
            'doc-platform': 'web',
            # 'pdfs-host-id':'wikcnIoWN8Fzdx9z6xZ3zMdfaje' ,
            'pdfs-host-type': 'Wiki',
            'referer': f'https://definesys.feishu.cn/wiki/{node_token}',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'x-csrftoken': self.csrf_token
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        #t = json.loads(response.text)

        result = json.loads(response.text).get("data").get("result")
        """
        "job_status": 0,
                "job_error_msg": "success",
                "file_extension": "pdf",
                "file_name": "aPaaS部署安装",
                "file_size": 21581,
                "file_token": "KTeOblJaZo77mrxMIpLcoUjznTf",
                "extra": {},
                "type": "docx"
        """
        if result is None or result.get("job_status", 2) == 2:
            # print("文档还未渲染完毕，等待后重试……")
            lark.logger.info("文档还未渲染完毕，等待后重试……")
            #print(result)
        return result

    def download_file(self, file_token, file_path):
        url = f"https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/all/{file_token}/"
        payload = {}
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh,en;q=0.9,zh-CN;q=0.8',
            'Connection': 'keep-alive',
            'Cookie': self.cookies
        }
        response = requests.request("GET", url, headers=headers, data=payload)

        # print(response.text)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        #print('文件保存成功！')
        lark.logger.info(f"【下载成功】{file_path}")

    # def download_docx_file(self):


# if __name__ == '__main__':
#     #client = FeishuDriveClient('u-feem5zVY10hHIjomQS6uyx1hjyxhhgZzWU0000Sywb5x')
#     # client.user_access_mode(user_access_token="u-c4KIEFvy5ev9qfHHdwhdrw1hj03hhgtFV800l4CywalQ")
#     # client.get_root_list()
#     # 获取根空间
#     #print(client.get_files_list(client.root_doc_token, None, 200))
#
#     #print(client.get_app_access_token())
#     #print(client.root_doc_token)
#     #飞书知识空间
#     user_access_token = "u-c4WshwOYR6GFKhQyUGcqCL1hjE1Nhg_3WE00g5CywfkA"
#     cookies = "passport_web_did=7326876814088028161; QXV0aHpDb250ZXh0=30d56d60103f4e0e92df7b4fd70ba033; trust_browser_id=e2a2eb96-c801-44e9-afa1-bb47f75a56c5; __tea__ug__uid=7326876760669947429; login_recently=1; lang=zh; et=a95c1f972e884617591048db8ff6a950; vt=1; ot=a95c1f972e884617591048db8ff6a950; passport_trace_id=7387376815553789956; Hm_lvt_e78c0cb1b97ef970304b53d2097845fd=1720007981; Hm_lpvt_e78c0cb1b97ef970304b53d2097845fd=1720007981; is_anonymous_session=; Hm_lvt_a79616d9322d81f12a92402ac6ae32ea=1723516438; HMACCOUNT=C6B641E8D7CC8CB8; bitable_tableId_viewId_history=%7B%22I978bzTaIaCEdQsdndPchvhBn3e%22%3A%7B%22tableId%22%3A%22tblY1PkfLlZsQ58w%22%2C%22viewId%22%3A%22vewHY3Elm9%22%7D%2C%22bascnhGWblUtN5QK5ydpCSyiJud%22%3A%7B%22tableId%22%3A%22tblG8jIqgpAMA6oa%22%2C%22viewId%22%3A%22vewW3Jw38L%22%7D%2C%22DCBIbAFEVa2bdasVnYAccPnqnJc%22%3A%7B%22tableId%22%3A%22tblVGGR6dQtJC4nB%22%2C%22viewId%22%3A%22vewoTuiVgT%22%7D%7D; meego_csrf_token=qKxTk3PV-BVZg-PIbF-0Wp3-qacGnpUJBLf8; session=XN0YXJ0-597j44f9-f266-49a9-b49e-4324ea7a68a9-WVuZA; session_list=XN0YXJ0-e65t1c08-62c0-4ea4-8c9e-06c402a2bd79-WVuZA_XN0YXJ0-597j44f9-f266-49a9-b49e-4324ea7a68a9-WVuZA_XN0YXJ0-597j44f9-f266-49a9-b49e-4324ea7a68a9-WVuZA; Hm_lpvt_a79616d9322d81f12a92402ac6ae32ea=1724211646; _uetvid=1ddc99f0393311ef9cfba1c30eacb2a6; _csrf_token=f9c370ad2eb751489ac0a1d1d6880673f0108169-1729300886; msToken=TxPY70P3tVBQzKonuWxm2o8taQ_SWBSt3vQpSe_SV290JOQP5-x7YhgjekZerfFRsgq8zRNw9sYpPOzMvgG1iMhUtwdfiX6uo_Sm9JuPpv16oiFPXBAmYNNcrTwSIm2VAhv6; _gcl_au=1.1.147057443.1730436817; locale=zh-CN; csrf_token=; m_65f68ea2=; _gid=GA1.2.167477669.1731641669; msToken=0B1tIcYFqRlWLld98BcLIjvxo3GLhNyS1fNxUoM7HXyqBpIvlHuFKaVsYikwAw_bdwSaMEu3GwaKyEnsGsYD9vlzOiNcxZ66x4Gy3lwDNz7BEAN2zA5UJZmkVknmOBx05gZQ9mNxqHTH-PshdsgikI3P5MTTFCmD8awN4Vf2HzoQzMMLhbw6; _ga=GA1.2.726367516.1705921445; js_version=1; lgw_csrf_token=a973c86fe85de576d965b58d0a2b12e2b7075b02-1731652064; _ga_VPYRHN104D=GS1.1.1731660192.25.1.1731660975.11.0.0; sl_session=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzE3MDc2ODEsInVuaXQiOiJldV9uYyIsInJhdyI6eyJtZXRhIjoiQVYxbDNaRkx3QUVJWFdUZ0RSMkFBUTVscmt1a21NTkFBV1d1UzZTWXcwQUJacjZ1bWx0Q3dBTUNLZ0VBUVVGQlFVRkJRVUZCUVVKdGRuRTJZV0ZuYVVGQmR6MDkiLCJzdW0iOiI3YzgzNzI5YWQ2ZjI2ZmUyNmVmZWNhYjM2MGMyYTA5YzlkOWIzOGFiYjU5YTc5OTQ1NWZkOTdkYWExOTYyMjg0IiwibG9jIjoiemhfY24iLCJhcGMiOiJSZWxlYXNlIiwiaWF0IjoxNzMxNjY0NDgxLCJzYWMiOnsiVXNlclR5cGUiOiI0MiIsIlVzZXJTdGFmZlN0YXR1cyI6IjEifSwibG9kIjpudWxsLCJucyI6ImxhcmsiLCJuc191aWQiOiI2NzMwMDI4ODM0Mjg1OTQ1MDk2IiwibnNfdGlkIjoiNjcyOTc1MDA5MDEzMjQ4ODQ2MiIsIm90IjozfX0.ULrhCvve4fC1FdESpjr5Z9-yUhLm9PZa6xXF0cp96gSgUj9oFxu_biY3jPJtoS6QVykKySBmDPbqhUSg1Vuhyw; template-branch-list=; passport_app_access_token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzE3MDc5NTgsInVuaXQiOiJldV9uYyIsInJhdyI6eyJtX2FjY2Vzc19pbmZvIjp7IjI5Ijp7ImlhdCI6MTczMTY2NDc1NywiYWNjZXNzIjp0cnVlfSwiMiI6eyJpYXQiOjE3MzE2NjMzMTUsImFjY2VzcyI6dHJ1ZX0sIjE0MyI6eyJpYXQiOjE3MzE2NjQ3NTgsImFjY2VzcyI6dHJ1ZX19LCJzdW0iOiI3YzgzNzI5YWQ2ZjI2ZmUyNmVmZWNhYjM2MGMyYTA5YzlkOWIzOGFiYjU5YTc5OTQ1NWZkOTdkYWExOTYyMjg0In19.55b_GXzsowlFesli9nJ4p6wUpF2iZ191_A_2RauzYYbL3NofO62XfjQm5eJ0mbi-VDZq8HYT38SO_7PuG2R7tQ; swp_csrf_token=67dd5d83-f34b-4009-bdac-c8ebe56ce381; t_beda37=b15373ad6cc804d5dfddea99f32964e4f1f5f2235669562151e427453b53a99a; ccm_cdn_host=//lf-scm-cn.feishucdn.com"
#     csrf_token = "f9c370ad2eb751489ac0a1d1d6880673f0108169-1729300886"
#     space_client = FeishuSpaceClient(user_access_token, cookies, csrf_token)
#     spaces = space_client.get_all_spaces_list(None, 50)
#     for space in spaces:
#         #print(lark.JSON.marshal(space, indent=4))
#         space_info = space_client.get_space_info(space.space_id)
#         #print(lark.JSON.marshal(space_info, indent=4)) => 没必要再获取了，跟space_list中的item数据一样
#         # 用一个测试
#         break;
