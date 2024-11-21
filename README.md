# feishu_docs_migration_tool
飞书文档库（云盘、知识库）导出工具

# 作用
用户可以把自己飞书云盘中的个人文件夹、共享文件夹、知识库等，同步到本地

# 使用方法
## 编辑 file_syncer.py
设置同步文件夹、获取飞书的token、cookies等参数后运行即可

## 相关参数获取
### Part 1. user_access_token:
https://open.feishu.cn/api-explorer 任意应用直接获取一个即可，每次有效期是1200s， 
除了user_access_token 最好每次同步前更新一次，cookies 和 csrf_token 基本可以一次性用很久。够自己同步完一轮。


### Part 2. cookies 和 csrf_token获取方式：
1. 进入 https://domain_name.feishu.cn/wiki/ 比如 https://definesys.feishu.cn/wiki/；
2. 选择任意知识库的任意文档浏览器中打开，并打开浏览器的审查元素，监控网络请求，开始抓包；
3. 选择右上角“下载为” => “word”；
4. 在网络连接中选择名称为 create/?synced_block_host_token=xxxxx的网络请求，复制其中的Cookie、X-Csrftoken即可

