# 以后部署（Deploy Later）

> ⚠️ **本文全部内容需要 Mike 确认后再执行。** 目前没有部署，没有运行。下面只是方案说明，没有任何一步被实际执行过。
> 信息来源：Dify 官方文档与定价页（2026-10-26 查阅）。免费额度、价格、系统要求会变化，执行前请重新打开官方页面核对。

## 方案对比

| | 方案 A：Dify Cloud 免费 Sandbox（推荐） | 方案 B：自己用 Docker 部署（不推荐现在做） |
|---|---|---|
| 需要什么 | 一台能上网的电脑（手机浏览器不建议，画布操作不方便）+ 邮箱/账号 | 一台电脑，官方文档写的最低要求为 CPU ≥ 2 核、内存 ≥ 4 GiB，并安装 Docker 和 Docker Compose |
| 费用 | 定价页显示有免费 Sandbox 套餐（"For trying out Dify's core features. Free"）。具体额度以官网为准 | Dify 社区版免费，但需要自己的电脑/服务器和电费 |
| 难度 | 低：浏览器里注册即可 | 高：命令行、Docker、端口、升级、备份 |
| 模型 | 需要配置模型供应商（Model Provider）；是否有免费模型额度以官网为准 | 同样需要自己配置模型 API Key |
| 适合 Mike 吗 | ✅ 适合：电脑初学者、要免费、不想折腾环境 | ❌ 现在不适合 |

## 方案 A 步骤（需 Mike 确认）

1. 电脑浏览器打开 https://dify.ai/pricing 查看 Sandbox 当前额度 → **记下查看日期**
2. 打开 https://cloud.dify.ai 注册登录
3. 右上角头像 → 设置 → **Model Provider**，添加一个模型（选择免费/低价的；需 Mike 决定）
4. 顶部 **Knowledge** → 新建两个知识库：
   - `ev-knowledge`：上传 knowledge/01、02、03、05
   - `ev-glossary`：上传 knowledge/04
   - 两个库使用相同的索引设置（例如都用 High Quality）
5. 在知识库里用 **Retrieval Testing**（检索测试）试几个问题，确认能搜到
6. **Studio** → 创建应用 → 选 **Chatflow** → 名称 `EV`
7. 按 `dify/import-guide.md` 搭节点、粘提示词
8. 用右上角 **Preview** 按 `docs/test-cases.md` 逐条测试，把实际回答记录到 test-cases.md 的"实际结果"列
9. 满意后 **Publish**，得到网页链接（Web App），手机也能用
10. 在应用菜单 **Export App** 导出应用包，提交到本仓库 `dify/` 目录（届时才会有真正可导入的文件）

## 方案 B 概要（以后有自己电脑时再考虑，需 Mike 确认）

官方文档：https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose

大致流程（只是概要，不是可直接照做的完整步骤，请以官方文档为准）：
1. 安装 Docker Desktop（Windows 需要 WSL 2）
2. 按官方文档 `git clone` Dify 源码
3. 进入 `dify/docker` 目录，复制环境变量示例文件，`docker compose up -d`
4. 浏览器打开本机地址完成初始化
5. 之后同方案 A 第 3–10 步

## 不要做的事

- 不要为了这个项目花钱买服务器或付费套餐（除非 Mike 以后明确决定）
- 不要把模型 API Key、密码提交到这个公开仓库
- 不要导出带 "Export secret values" 的应用包到公开仓库
