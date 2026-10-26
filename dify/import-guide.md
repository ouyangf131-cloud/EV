# 在 Dify 中手工搭建 EV Chatflow（Import / Build Guide）

> ⚠️ **重要说明：**
> - `dify/chatflow-design.json` 是本仓库自定义格式的**结构化设计文件**，**不是 Dify 官方 DSL**，**不能**用 Dify 的「Import App / 导入应用」直接导入。
> - 原因：Dify 官方导出格式（`.ifpkg` 应用包，内含 `app.yaml` DSL）字段较多且随版本变化，在没有可运行的 Dify 实例来导出、核对的情况下，手写一份可能导入失败或产生错误配置。
> - 正确做法：按下面步骤**在 Dify 界面手工搭建**；搭好并测试后，用 **Export App** 导出真正的应用包，再提交到本目录。
> - 本指南**没有被实际执行过**，界面文字以搭建当天的 Dify 版本为准（参考文档查阅日期：2026-10-26）。

预计时间：30–60 分钟（估计值，新手可能更久）。

## 第 0 步：准备

- 已按 `docs/deploy-later.md` 注册 Dify Cloud（或自部署），并配置好一个模型（Model Provider）
- 已创建知识库 `ev-knowledge`（01、02、03、05）和 `ev-glossary`（04），并用 Retrieval Testing 试过能搜到内容

## 第 1 步：创建应用

1. **Studio** → **Create from Blank / 创建空白应用**
2. 类型选 **Chatflow**
3. 名称：`EV`；描述：新能源汽车维修学习助手
4. 画布上默认已有 **User Input**（开始）、LLM、Answer 节点；可以删掉默认的 LLM 和 Answer，后面重新加

## 第 2 步：创建会话变量

画布右上角 **Conversation Variables** → 添加以下 9 个，类型都选 **String**，默认值留空：

`brand`、`vehicle_model`、`model_year`、`powertrain`、`mileage`、`power_state`、`symptom`、`warning_info`、`recent_events`

## 第 3 步：意图分类（LLM）

1. 在 User Input 后面加 **LLM** 节点，标题改为 `意图分类`
2. 选模型，temperature 调低
3. SYSTEM：复制 `docs/system-prompts.md` §2 全文
4. USER：插入用户输入变量（`userinput.query`，旧界面可能叫 `sys.query`）
5. 打开 **Memory**

> **更简单的备选：** 用 **Question Classifier** 节点代替第 3、4 步。添加 5 个 class，标题分别为 `fault`、`knowledge`、`english`、`unsafe_hv`、`out_of_scope`，描述复制 §2 的标签定义；把"危险高压请求优先归 unsafe_hv"写进 **Instructions**。每个 class 直接连到对应分支。

## 第 4 步：分流（If-Else）

在意图分类后加 **If-Else**，标题 `分流`，按顺序配置（变量都选 `意图分类` 的 `text`，运算符选 **Contains**）：

| 分支 | 值 |
|------|----|
| IF | `unsafe_hv` |
| ELIF | `fault` |
| ELIF | `knowledge` |
| ELIF | `english` |
| ELSE | （无条件） |

## 第 5 步：故障分支

1. ELIF `fault` → **Parameter Extractor**，标题 `槽位提取`
   - Input：用户输入变量
   - 参数：9 个（名字同会话变量），全部 String、非必填，描述参考 `docs/workflow-nodes.md` §1
   - Instruction：复制 `docs/system-prompts.md` §3，把 `{{#conversation.xxx#}}` 替换为变量选择器中的对应会话变量
   - **待实测**：官方文档没有明说 Parameter Extractor 的 Instruction 能否插入会话变量。如果不能插入，可以去掉 Instruction 里"已记录的信息"那一段（`合并槽位` 节点仍会保留旧值），或者在前面加一个 Template 节点把旧值和用户输入拼在一起作为 Input
2. → **Code**，标题 `合并槽位`（语言 Python 3）：
   - 输入变量 19 个：`is_success` ← `槽位提取` 的 `__is_success`；`new_brand`…`new_recent_events` ← `槽位提取` 的 9 个同名参数；`old_brand`…`old_recent_events` ← 9 个同名会话变量
   - 代码：复制 `docs/workflow-nodes.md` §2.1 里的 python 代码块
   - 代码也可以直接复制仓库里的 `dify/code_merge_slots.py`（与 §2.1 逐字相同）
   - 输出变量 10 个，类型都选 **String**：9 个同会话变量名，加 `fault_query`
   - 作用：提取失败（`__is_success=0`）时全部沿用旧值；某项新值为空时保留旧值；"不知道/未知/unknown/不清楚"等统一成「不确定」，且「不确定」不会覆盖已确定的旧值；`fault_query` 是拼好的检索词
   - 如果 Dify 报错不允许 `import re`，需要改写代码并重新跑 `tests/test_code_merge_slots.py`（**待实测**）
3. → **Variable Assigner**，标题 `保存槽位`：9 行，每行 会话变量 ← `合并槽位` 的同名输出（**不是**直接用 `槽位提取` 的参数），模式 **Overwrite**
4. → **If-Else**，标题 `信息是否齐全`：IF 条件（AND）对 `brand`、`vehicle_model`、`power_state`、`symptom` **每个**都加两条：**is not empty** 和 **not contains** `不确定`（共 8 条；"不确定"不算齐全，继续问诊）
5. IF → **Knowledge Retrieval**（`排查资料检索`，Query Text = `合并槽位` 的 `fault_query`（不是用户输入），知识库 `ev-knowledge`）→ **LLM**（`排查方向`，Context = 上一节点 `result`，SYSTEM 复制 §5，开 Memory）→ **Answer**（内容插入 `排查方向.text`）
6. ELSE → **Knowledge Retrieval**（`问诊清单检索`，同上，可选）→ **LLM**（`信息收集`，SYSTEM 复制 §4）→ **Answer**

## 第 6 步：知识分支

ELIF `knowledge` → **Knowledge Retrieval**（`知识检索`，`ev-knowledge`）→ **LLM**（`知识问答（带引用）`，Context = `result`，SYSTEM 复制 §6）→ **Answer**

确认右上角 **Features** 中 **Citation and Attributions**（引用与归属）为开启状态。

## 第 7 步：英语分支

ELIF `english` → **Knowledge Retrieval**（`术语检索`，`ev-glossary`）→ **LLM**（`术语+例句+对话`，Context = `result`，SYSTEM 复制 §7）→ **Answer**

## 第 8 步：安全拒答

IF `unsafe_hv` 和 ELSE 两条线都连到同一个 **LLM**（`安全拒答模板`，SYSTEM 复制 §8，其中插入 `意图分类.text`）→ **Answer**

## 第 9 步：错误处理

每个 LLM 节点的错误处理（Error Handling）：开启重试；失败时使用默认值：
`抱歉，系统暂时没能生成回答。请稍后再试；涉及安全的问题请直接咨询有资质的技师。`

## 第 10 步：测试与导出

1. 点 **Preview**，按 `docs/test-cases.md` 逐条测试，每条新开会话
2. 在 test-cases.md 的"实际结果"栏写：通过/不通过、日期、模型名称、备注
3. 不通过 → 修改对应提示词 → 重测
4. 全部满意后 **Publish**
5. 应用菜单 → **Export App**（不要勾选 Export secret values）→ 把导出文件提交到本仓库 `dify/`，并更新 README 状态

## 对照检查表

- [ ] 9 个会话变量
- [ ] 1 个意图分类（LLM 或 Question Classifier）
- [ ] 2 个 If-Else（或 1 个，若用 Question Classifier）
- [ ] 1 个 Parameter Extractor + 1 个 Code（合并槽位）+ 1 个 Variable Assigner
- [ ] `信息是否齐全` 里 4 个必填项都有 not contains `不确定`（共 8 条条件）
- [ ] `排查资料检索` 的 Query Text 是 `合并槽位.fault_query`
- [ ] 4 个 Knowledge Retrieval
- [ ] 6 个 LLM（含意图分类）
- [ ] 5 个 Answer
- [ ] 共 21 个节点（与 `dify/chatflow-design.json` 一致；若用 Question Classifier 则少 1 个 If-Else）
- [ ] 每个分支都以 Answer 结束
