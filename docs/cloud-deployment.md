# CloudBase 部署准备

当前阶段：已实现 AI 接口、CloudBase HTTP 数据存储、小程序云端调用、共享设置及本机数据复制。尚未完成云端部署、SQL 事务函数执行和真机联调。

## 上传设置

- 本地代码上传，压缩包：`dist/family-recipes-api.zip`。
- 服务名：`family-recipes-api`。
- 服务端口：`8080`；访问端口保留平台默认值。
- Dockerfile：有，名称 `Dockerfile`，位于压缩包根目录。
- 自动启停，最小 0、最大 1 个实例。公网默认域名保持关闭。
- 启动命令由 Dockerfile 提供，无需覆盖。

## 环境变量

- `DEEPSEEK_API_KEY`：原有 DeepSeek 密钥。
- `DEEPSEEK_MODEL`：`deepseek-v4-flash`。
- `TAVILY_API_KEY`：原有 Tavily 密钥。
- `CLOUDBASE_ENV_ID`：现有 CloudBase 环境 ID。
- `CLOUDBASE_API_KEY`：仅后端使用的 CloudBase API Key，从本地 `.env.cloud` 复制到云托管环境变量。
- `FAMILY_ACCESS_TOKEN`：使用密码管理器生成的至少 32 位随机 ASCII 字符，作为家庭共同的访问凭证。不得放入小程序源码；后续由家庭成员在设备上输入。撤销访问时更换此值。

目前只有 `/health` 无需凭证。业务接口必须携带 `Authorization: Bearer <家庭凭证>`；本机的 `X-Recipe-Client` 无法通过云端验证。未配置家庭凭证时业务接口返回 503。

此阶段不区分家庭成员。家庭凭证不等于微信登录或成员权限管理。小程序默认仍用本机数据；在首页“家庭共享设置”输入家庭凭证并验证连接成功后，才切换云端。这里不能填写 CloudBase API Key。

小程序通过 `wx.cloud.callContainer` 连接 `family-recipes-api`，部署前需要将小程序与该环境关联。关闭公网域名后仍可通过关联的小程序调用，参见 [小程序访问说明](https://docs.cloudbase.net/run/develop/access/mini)。

## 打包与验证

运行 `backend/build_cloud_package.py`。脚本按文件白名单构建 ZIP，不包含 `.env`、`search.env`、本地菜谱或小程序代码。Dockerfile 也使用明确的文件列表。

本地 WSGI 测试覆盖缺少配置、拒绝本机头、授权成功、请求体格式和大小、健康检查；未在 Windows 上运行 Linux 容器，实际镜像构建和云端连通性待验证。

服务使用一个进程，保留现有搜索候选缓存和 AI 并发锁。实例缩容、重启后候选缓存失效，需要重新搜索；不会自动再次调用付费接口。

## 数据库和验证进度

`schema.sql` 已由用户在控制台执行，两张表的 RLS 已确认开启；API Key 对两表的只读请求已成功。还需在 SQL 编辑器以管理员运行 `shopping_transaction.sql`，它增加批量清单事务及防重复操作记录。失败会回滚整批修改，重试相同操作不会重复增加数量。

菜谱修改使用版本条件更新；冲突保留用户表单，不覆盖云端版本。买菜清单保留同名同单位数字合并规则，批量写入由 RPC 事务处理。事务冲突需刷新清单后重试。返回页面时重新读取，暂不实时推送。

本机数据复制由用户点击确认，保留本机原件；同编号不同菜谱跳过而不覆盖。清单复制保留购买状态，同编号跳过，复制过程可重试。

自动检查：28 项 Python 测试通过；JS/JSON/WXML 表达式语法通过；模拟测试确认本地合并、购买状态、云端重试操作 ID、版本和来源保留。尚未实际构建 Linux 镜像或验证云端事务执行及多手机调用。

参考：[CloudBase PostgreSQL 连接说明](https://docs.cloudbase.net/database/postgresql/connecting-to-postgresql)、[Gunicorn 配置](https://gunicorn.org/reference/settings/)。
