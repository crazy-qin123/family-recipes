# 搜索菜名配置与验证

1. 本地打开 `D:\codexworkspace\family-recipes\backend\search.env`。
2. 在 `TAVILY_API_KEY=` 后填写 Tavily Key 并保存，不要发到聊天里。此文件已排除 Git，位于小程序代码目录之外。现有 DeepSeek 配置无需改动。
3. 首次更新代码后重启 Python 后端；以后只修改 Key 无需重启。
4. 微信开发者工具重新编译，点击“添加菜谱 → 搜索菜名”，输入菜名并搜索。
5. 查看来源和摘要，选择其中一份做法。AI 只整理这一来源，确认表单后才保存。

当前仅本机模拟器可连接后端，未部署家庭共享服务。未配置搜索 Key 时提示配置，不会伪造搜索结果。

搜索采用 Tavily basic，最多5条，不请求 Tavily 生成答案。使用服务返回的 `raw_content` 作为正文，不用摘要代替完整菜谱。没有正文、正文过长或出现验证码的候选无法直接整理，可复制来源链接后自行查看，改用粘贴正文。

当前仍排除下厨房搜索结果以减少已知访问受限来源。即使取得正文，也不保证一定包含完整菜谱；DeepSeek 会拒绝无法识别的内容，成功草稿仍需人工核对。

搜索记录及正文仅缓存在内存，最长30分钟，最多100条；重启后失效，不保存原网页文件。同一结果成功整理后再次打开使用缓存草稿，避免重复模型调用。不同来源不拼接。来源链接由后端保存，不采用模型生成的链接。

联网阶段将菜名发送给 Tavily；选择整理时将所选网页正文发送给 DeepSeek。两家额度独立；不自动重试失败的付费请求。接口没有家庭认证，只适合当前本机开发。

2026-09-09 核实：Tavily 提供每月1,000免费 credits；basic 搜索每次1 credit，政策以控制台为准。

首次真实联调：当前本机环境搜索“番茄炒蛋”成功返回5个来源。选择 `https://icook.tw/recipes/460543` 后，DeepSeek 返回6项食材、8个步骤，原来源链接正确保留。测试未保存菜谱。部分搜索结果为繁体中文，部分来源没有正文；成功提取不等于人工审核通过。此次结果仅证明当前环境单次连通，不代表中国大陆所有网络或后续时段稳定可用。

参考：

- https://docs.tavily.com/documentation/api-credits
- https://docs.tavily.com/documentation/api-reference/endpoint/search

验证命令：在 backend 目录运行 `python -m unittest -v test_importer test_server test_deepseek_recipe test_search_recipe`。搜索测试使用合成结果，不能替代实际服务验证。
