import logging
import time, os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from lark_oapi.api.drive.v1 import ListFileResponseBody, File, GetExportTaskResponseBody, GetExportTaskResponse
import lark_oapi as lark
from typing import Any, Optional, Union, Dict, List, Set, IO, Callable, Type

from lark_oapi.api.wiki.v2 import Node

from feishu.feishu_client import FeishuDriveClient, FeishuSpaceClient
from aPaaS.apaas_client import APaaSClient


class LocalFileSyncer():

    OVER_WRITE  = False #如何同步时文件已经存在，是覆盖还是跳过，建议跳过。
    DRIVE_PATH = "/drive"
    SPACE_PATH = "/space"
    aPaaS = APaaSClient()
    def __init__(self, root_local_path):
        self.root_local_path = root_local_path
        self.SPACE_PATH = root_local_path + self.SPACE_PATH
        self.DRIVE_PATH = root_local_path + self.DRIVE_PATH

    def is_file_exists(self, file_path: str) -> bool:
        if file_path is None:
            return False
        file = os.path.exists(file_path)
        if not file:
            return False
        else:
            return True

    def mkdir(self, root_path, folder_name):
        legal_folder_name = folder_name.replace(".", "_")
        if not self.is_file_exists(root_path + "/" + legal_folder_name):
            os.makedirs(root_path + "/" + legal_folder_name)

    def set_drive_client(self, client: FeishuDriveClient):
        self.drive_client = client

    def set_space_client(self, client: FeishuSpaceClient):
        self.space_client = client

    def sync_drive_file_to_local(self, file_info, parent_path):
        extension = ""
        """ doc_type：
                doc：旧版文档
                docx：新版文档
                sheet：电子表格
                bitable：多维表格
                mindnote：思维笔记
                wiki：知识库文档
                file：文件
            drive里的file自带后缀
        """
        if file_info.type in ["file"]:
            extension = ""  # file类型通常名称自带后缀
        elif file_info.type in ["docx", "doc"]:
            extension = "docx"
        elif file_info.type in ["sheet"]:
            extension = "xlsx"
        elif file_info.type in ["wiki"]:
            extension = "md"
        else:
            lark.logger.error(f"不支持的文件类型，建议手工处理：{file_info.type}, 文件：{file_info.name}")
            # self.aPaaS.new_bitables(
            #     file_info.name, file_info.token, 'drive', file_info.url,parent_path, file_info.created_time,
            #     file_info.modified_time)
            return
        if file_info.type in ["file"]:
            try:
                extension = file_info.name.split(".")[1]
            except Exception:
                extension = ""
            file_path = f"{parent_path}/{file_info.name.replace('/', '-')}"
        else:
            file_path = f"{parent_path}/{file_info.name.replace('/','-')}.{extension}"
        #lark.logger.info(f"【SYNC FILE】 to {file_path} 【doc_type:{file_info.type}】")
        if file_info.type in ['doc','sheet','docx']: #'bitable'
            if not self.OVER_WRITE:
                if self.is_file_exists(file_path):
                    lark.logger.info(f"【SYNC NOTICE】{file_path} 文件已存在，跳过")
                    return
            ticket = self.drive_client.download_document_buy_ticket(file_info.token, file_info.type, extension)
            ticket_response: GetExportTaskResponse = self.drive_client.download_document_check_ticket(ticket, file_info.token)
            waiting_count = 0
            # 买票、查票、下载
            while ticket_response.code == 0 and ticket_response.data.result.job_status != 0:
                time.sleep(1)
                waiting_count += 1
                lark.logger.info(f"{file_info.name} 下载，等待文件渲染中`... {waiting_count}")
                ticket_response = self.drive_client.download_document_check_ticket(ticket, file_info.token)
            self.drive_client.download_file(ticket_response.data.result.file_token, file_path)
        elif file_info.type in ['file']:
            if not self.OVER_WRITE:
                if self.is_file_exists(file_path):
                    lark.logger.info(f"【SYNC NOTICE】{file_path} 文件已存在，跳过")
                    return
            self.drive_client.download_document_get_file(file_info.token, file_path)
        else:
            # self.aPaaS.new_bitables(
            #     file_info.name, file_info.token, 'drive', file_info.url, parent_path, file_info.created_time, file_info.modified_time)
            lark.logger.warning(f"【SYNC NOTICE】不支持的文件类型，建议手工处理：{file_info.type}, 文件：{file_info.name}")

    def sync_drive_to_local(self, folder_token, page_token, path_level, parent_path):
        path_level += 1  #从0级目录开始
        #files = List[File]()
        self.mkdir(parent_path, "")
        files_response: ListFileResponseBody = self.drive_client.get_files_list(folder_token, page_token, 200)
        page_token = files_response.next_page_token
        files = files_response.files
        while page_token:
            new_files_response = self.drive_client.get_files_list(folder_token, files_response.next_page_token, 200)
            page_token = new_files_response.next_page_token
            files.extend(new_files_response.files)
            #文件清单扩充
        print(files)
        for file_info in tqdm(files, desc=f"【{path_level}】{parent_path} 文件同步...", leave= False):
            # drive类型的文件name包含了必要的后缀
            if file_info.type == 'folder':
                # 如果是文件夹，递归调用sync_folder_to_local
                sub_path = parent_path + '/' + file_info.name.replace('/', '-')
                self.sync_drive_to_local(file_info.token, None, path_level, sub_path)
            else:
                # 如果是文件，执行同步操作
                self.sync_drive_file_to_local(file_info, parent_path)
            continue

    def sync_space_to_local(self, space_id, parent_node_token, path_level, parent_path):
        path_level += 1
        #self.mkdir(parent_path, self.space_client.get_space_info(space_id).name.replace('/', '-')) #创建上级目录
        #space_info = self.space_client.get_space_info(space_id)
        nodes_response = self.space_client.get_files_list(space_id, parent_node_token, None)
        if not nodes_response:
            raise Exception("获取空间节点失败")
        page_token = nodes_response.page_token
        has_more = nodes_response.has_more
        nodes = nodes_response.items
        while has_more and page_token:
            new_nodes_response = self.space_client.get_files_list(space_id, parent_node_token, page_token)
            page_token = new_nodes_response.page_token
            has_more = new_nodes_response.has_more
            nodes.extend(new_nodes_response.items)

        """
            space node 的文档跟drive的文档有区别
            本身可能同时即是文件夹，又是文件
            通过 node.has_child 判断
        """
        for node in tqdm(nodes, desc=f"【{path_level}】{parent_path} 文件同步...", leave= False):
            # print(lark.JSON.marshal(node, indent=4))
            #lark.logger.info(f"同步 {lark.JSON.marshal(node, indent=4)}")
            sub_path = parent_path + '/' + node.title.replace('/', '-')
            title = node.title
            parent_node_token = node.node_token
            is_folder = node.has_child
            ### 先处理文件下载，再处理子文件夹
            #self.mkdir(parent_path, title.replace('/', '-'))
            self.sync_space_file_to_local(node, sub_path)
            #print(f"Sync {sub_path} {title}")

            ### 递归子文件夹
            if is_folder:
                new_root = parent_path + "/" + title.replace("/", "-")
                self.mkdir(parent_path, title.replace("/", "-"))
                self.sync_space_to_local(space_id, parent_node_token, path_level, new_root)
            else:
                continue

    def sync_space_file_to_local(self, node: Node, sub_path: str):
        title = node.title.replace("/", "-")
        node_token = node.node_token
        obj_type = node.obj_type
        obj_token = node.obj_token

        # 判断是否要覆盖或者跳过
        if not self.OVER_WRITE:
            # 判断文件是否存在
            if self.is_file_exists(sub_path + "/" + title):
                lark.logger.info(f"【跳过同步】 {sub_path}/{title} 已存在，跳过")
                return

        if "docx".__eq__(obj_type) or "doc".__eq__(obj_type):
            self.mkdir(sub_path, title)
            # continue
            #print(f"=> {title} 是 {obj_type} ")
            #print(f"=> 尝试下载【{title}】 至 {sub_path} : node_token:{node_token} , 下载目录是：{sub_path}/{title}")
            ticket = self.space_client.download_document_buy_ticket(node_token, obj_token, obj_type)
            ticket_info = None
            while ticket_info is None or ticket_info.get("job_status", 2) == 2:
                ### 取决于文档大小，阻塞等待下载完成
                ticket_info = self.space_client.download_document_check_ticket(ticket, obj_token, node_token, obj_type)
                time.sleep(1)
                # 通常等几秒就好使了
            # {'file_name': 'aPaaS部署安装', 'file_size': 21571, 'file_token': 'FsW0bjdGToCkXuxze5zc3oGxnLf', 'extra': {}, 'type': 'docx', 'job_status': 0, 'job_error_msg': 'success', 'file_extension': 'pdf'}
            file_path = sub_path + "/" + ticket_info.get("file_name").replace("/", "-") + "." + ticket_info.get(
                "file_extension")
            self.space_client.download_file(file_token=ticket_info.get("file_token"), file_path=file_path)
        elif "file".__eq__(obj_type):
            # file 类型的下载
            # file 类型不建文件夹，直接down
            lark.logger.info(f"=> {title} 是 {obj_type} ")
            #file_path = sub_path + "/" + title.replace("/", "-")
            lark.logger.info(f"=> 尝试下载【{title}】 至 {sub_path} : node_token:{node_token} , 下载目录是：{sub_path}")
            # 差异是使用的是obj_token，而且不需要"买票"
            self.space_client.download_file(file_token=obj_token, file_path=sub_path)
        else:
            lark.logger.error(f"{title} 是 {obj_type} ,暂未支持下载。目标目录：{sub_path}")


def sync_drive_mine(user_access_token, local_root_path, cookies):
    """
    同步个人飞书云盘到本地
    """
    drive_client = FeishuDriveClient(user_access_token=user_access_token, cookies=cookies)
    # client.user_access_mode(user_access_token=user_access_token)
    drive_client.load_root_list()
    localFileSyncer = LocalFileSyncer(local_root_path)
    localFileSyncer.set_drive_client(drive_client)
    apaas = APaaSClient()
    # 创建根文件夹
    # apaas.new_root(root_token=client.root_doc_token, user_id=client.root_doc_user_id)
    root_doc_token = drive_client.root_doc_token
    localFileSyncer.sync_drive_to_local(root_doc_token, None, 0, localFileSyncer.DRIVE_PATH)

def sync_drive_shared(user_access_token, local_root_path, cookies):
    """
    同步个人飞书云盘到本地
    """
    drive_client = FeishuDriveClient(user_access_token=user_access_token, cookies=cookies)
    # client.user_access_mode(user_access_token=user_access_token)
    #drive_client.load_root_list()
    localFileSyncer = LocalFileSyncer(local_root_path)
    localFileSyncer.set_drive_client(drive_client)

    shared_folders_key, shared_folders_entities = drive_client.load_shared_list()
    for folder in tqdm(shared_folders_key, desc=f"【同步共享文件】", leave=False):
        folder_name = shared_folders_entities[folder].get('name')
        #lark.logger.info(folder_name)
        localFileSyncer.sync_drive_to_local(folder, None, 0, f"{local_root_path}/shared_drive/{folder_name}")

    # 创建根文件夹
    # apaas.new_root(root_token=client.root_doc_token, user_id=client.root_doc_user_id)
    # root_doc_token = drive_client.root_doc_token
    # localFileSyncer.sync_drive_to_local(root_doc_token, None, 0, localFileSyncer.DRIVE_PATH)



def sync_spaces(user_access_token, local_root_path, cookies, csrf_token):
    localFileSyncer = LocalFileSyncer(local_root_path)
    space_client = FeishuSpaceClient(user_access_token, cookies, csrf_token)
    localFileSyncer.set_space_client(space_client)
    spaces = space_client.get_spaces_list(None, 50)
    for space in tqdm(spaces.items, desc=f"【同步知识库】", leave=False):
        # print(lark.JSON.marshal(space, indent=4))
        space_info = space_client.get_space_info(space.space_id)
        tqdm.write(f"知识库：【{space_info.name}】 同步中...")
        # print(lark.JSON.marshal(space_info, indent=4)) => 没必要再获取了，跟space_list中的item数据一样
        current_space_path = localFileSyncer.SPACE_PATH + "/" + space_info.name
        localFileSyncer.mkdir(localFileSyncer.SPACE_PATH, space_info.name)
        localFileSyncer.sync_space_to_local(space_id=space.space_id,
                                            parent_node_token="",
                                            path_level=0,
                                            parent_path=current_space_path)

        # 可以先用一个测试
        # break


if __name__ == '__main__':
    local_root_path = "/Users/Downloads/feishu_documentes"

    user_access_token = ""
    cookies = ""
    csrf_token = ""
    """
        相关参数获取
        Part 1. user_access_token:
        https://open.feishu.cn/api-explorer 任意应用直接获取一个即可，每次有效期是1200s， 
        除了user_access_token 最好每次同步前更新一次，cookies 和 csrf_token 基本可以一次性用很久。够自己同步完一轮。
        
        
        Part 2. cookies 和 csrf_token获取方式：
        1）进入 https://domain_name.feishu.cn/wiki/ 比如 https://definesys.feishu.cn/wiki/；
        2）选择任意知识库的任意文档浏览器中打开，并打开浏览器的审查元素，监控网络请求，开始抓包；
        3）选择右上角“下载为” => “word”；
        4）在网络连接中选择名称为 create/?synced_block_host_token=xxxxx的网络请求，复制其中的Cookie、X-Csrftoken即可
    """

    """
    使用建议：
    因为user_access_token的有效期，如果文件量较多，建议分批次同步，并设置 OVER_WRITE = False ，这样会跳过已导出的文件
    """
    # 1. 迁移 云盘-我的文件夹
    sync_drive_mine(user_access_token, local_root_path, cookies)

    # 2. 迁移 云盘-共享文件夹
    #sync_drive_shared(user_access_token, local_root_path, cookies)

    # 3. 迁移 我有权查看的所有知识库
    #sync_spaces(user_access_token, local_root_path, cookies, csrf_token)
