# 节点、变量与分支条件（Workflow Nodes）

> 状态：**设计稿**，尚未在 Dify 中搭建。变量引用写法（如 `{{#llm_classify.text#}}`）仅为示意；在 Dify 编辑器里请用变量选择器（输入 `/` 或 `{`）插入，实际显示可能不同。

## 1. 会话变量（Conversation Variables）

在 Chatflow 画布右上角的 **Conversation Variables**（会话变量）面板中创建。会话变量在同一个会话的多轮对话中持续保存，只能由 **Variable Assigner** 节点写入（见官方 Variable Assigner 文档）。

| 变量名 | 类型 | 默认值 | 含义 | 示例值 |
|--------|------|--------|------|--------|
| `brand` | String | 空 | 品牌 | Tesla / GAC Aion 埃安 / BYD 比亚迪 / Toyota / Nissan / Honda / VW / BMW / Mercedes-Benz |
| `vehicle_model` | String | 空 | 车型 | Model 3、AION S、海豚 Dolphin、bZ4X、Leaf、ID.4、iX3、EQA |
| `model_year` | String | 空 | 年款 | 2021 |
| `powertrain` | String | 空 | 动力类型 | BEV 纯电 / PHEV 插混 / HEV 油电混动 / 不确定 |
| `mileage` | String | 空 | 里程（用户原话，含单位） | 8 万公里 |
| `power_state` | String | 空 | 是否通电 / 能否进入 READY | 能READY / 不能READY / 12V都没电 / 不确定 |
| `symptom` | String | 空 | 症状描述 | 仪表提示"请检修动力系统"，无法行驶 |
| `warning_info` | String | 空 | 仪表提示、故障灯、**用户自己读到的**故障码（只记录，不解释成事实） | 黄色感叹号 |
| `recent_events` | String | 空 | 最近发生的事：涉水、碰撞、维修、充电时出现、天气等 | 昨天暴雨涉水 |

**必填槽位（判断"信息是否齐全"）**：`brand`、`vehicle_model`、`power_state`、`symptom`。
其余为"建议补充"，信息收集节点会一起问，但不阻塞排查方向输出。

## 2. 节点清单

| ID | 节点类型（Dify 名称） | 标题 | 输入 | 输出 | 说明 |
|----|----------------------|------|------|------|------|
| `start` | User Input | 开始 | 用户消息 | `userinput.query` | Chatflow 自动捕获用户本轮消息；本设计不加额外输入字段 |
| `llm_classify` | LLM | 意图分类 | `userinput.query`；Memory 开启（窗口建议小，如最近几轮，具体值待调） | `text`（单个标签） | 提示词见 system-prompts.md §2；temperature 建议低 |
| `if_route` | If-Else | 分流 | `{{#llm_classify.text#}}` | 5 条路径 | 条件见 §3 |
| `pe_slots` | Parameter Extractor | 槽位提取 | `userinput.query` + 当前会话变量（写进 instruction） | 9 个参数 | 指令见 system-prompts.md §3 |
| `va_slots` | Variable Assigner | 保存槽位 | `pe_slots` 的各参数 | 写入会话变量 | 操作模式 Overwrite |
| `if_slots` | If-Else | 信息是否齐全 | 会话变量 | 2 条路径 | 条件见 §3 |
| `kr_intake` | Knowledge Retrieval | 问诊清单检索（可选） | `userinput.query` | `result` | 知识库 `ev-knowledge`；可用 metadata 只检索 01 文件 |
| `llm_intake` | LLM | 信息收集 | Context = `kr_intake.result`；会话变量 | `text` | 只问缺失信息，不给结论 |
| `kr_fault` | Knowledge Retrieval | 排查资料检索 | `userinput.query` | `result` | 知识库 `ev-knowledge` |
| `llm_troubleshoot` | LLM | 排查方向 | Context = `kr_fault.result`；会话变量 | `text` | 输出"可能方向/待核实" |
| `kr_knowledge` | Knowledge Retrieval | 知识检索 | `userinput.query` | `result` | 知识库 `ev-knowledge` |
| `llm_knowledge` | LLM | 知识问答（带引用） | Context = `kr_knowledge.result` | `text` | 依据不足时说不知道 |
| `kr_glossary` | Knowledge Retrieval | 术语检索 | `userinput.query` | `result` | 知识库 `ev-glossary` |
| `llm_english` | LLM | 术语+例句+对话 | Context = `kr_glossary.result` | `text` | |
| `llm_refusal` | LLM | 安全拒答模板 | `userinput.query`、`llm_classify.text` | `text` | 处理 unsafe_hv / out_of_scope |
| `ans_intake` / `ans_troubleshoot` / `ans_knowledge` / `ans_english` / `ans_refusal` | Answer | 回复 | 对应 LLM 的 `text` | 回复用户 | 内容只放 `{{#<llm_id>.text#}}` |

## 3. 分支条件

### 3.1 If-Else「分流」（`if_route`）

LLM 输出可能带空格或换行，所以用 **Contains**（包含）而不是 Is（等于）。按顺序判断：

| 顺序 | 分支 | 条件 | 去向 |
|------|------|------|------|
| IF | 高压危险 | `llm_classify.text` **contains** `unsafe_hv` | `llm_refusal` |
| ELIF 1 | 故障 | `llm_classify.text` **contains** `fault` | `pe_slots` |
| ELIF 2 | 知识 | `llm_classify.text` **contains** `knowledge` | `kr_knowledge` |
| ELIF 3 | 英语 | `llm_classify.text` **contains** `english` | `kr_glossary` |
| ELSE | 超范围/无法识别 | （包括 `out_of_scope` 和任何意外输出） | `llm_refusal` |

为什么 `unsafe_hv` 放第一：保证"高压+故障"混合的危险请求优先走安全拒答。五个标签互相不包含，contains 不会串线。

### 3.2 If-Else「信息是否齐全」（`if_slots`）

| 分支 | 条件（AND） | 去向 |
|------|------|------|
| IF 齐全 | `conversation.brand` is not empty **AND** `conversation.vehicle_model` is not empty **AND** `conversation.power_state` is not empty **AND** `conversation.symptom` is not empty | `kr_fault` → `llm_troubleshoot` |
| ELSE 缺信息 | 其他 | `kr_intake` → `llm_intake` |

### 3.3 备选：用 Question Classifier 代替「LLM 意图分类 + If-Else」

Dify 官方有 **Question Classifier** 节点：输入变量（通常是用户 query）→ 选模型 → 定义多个 class（class 标题显示在画布上，class 描述给 LLM 看），每个 class 自动成为一条输出路径；还可以写 Instructions 处理边界情况。

| 对比 | LLM + If-Else（本设计默认） | Question Classifier（备选） |
|------|------|------|
| 节点数 | 2 个 | 1 个 |
| 可控性 | 提示词完全自定义，可以写详细的优先级规则 | 通过 class 描述 + Instructions 控制 |
| 调试 | 能直接看到 LLM 输出的标签文本 | 看走了哪个 class |
| 新手难度 | 稍高 | 更低，推荐新手先试 |

若改用 Question Classifier，5 个 class 描述可直接复制 system-prompts.md §2 中的标签定义，并把"高压安全优先"写进 Instructions。

## 4. Knowledge Retrieval 节点设置建议

依据官方文档：需要设置 **Query Text**（选 `userinput.query`）、选择知识库、配置 **Retrieval Setting**（Rerank / Weighted Score、Top K、Score Threshold）。输出变量为 `result`。

- Top K：建议从较小值开始（例如 3–5），根据测试调整（**建议值，未经测试**）
- Score Threshold：先关闭，测试后再决定是否开启
- 在 LLM 节点中：**Context** 选该节点的 `result`，并在系统提示词里引用 Context 变量

## 5. Answer 节点

每个分支一个 Answer 节点，内容只放对应 LLM 的输出变量。官方文档说明 Answer 节点按变量就绪顺序流式输出。

## 6. 错误处理（详见 safety-and-errors.md）

LLM 节点支持重试与失败兜底（默认值 / 错误分支 / 备用模型，以当前版本界面为准）。建议所有 LLM 节点设置"默认值"兜底文本：
`抱歉，系统暂时没能生成回答。请稍后再试；涉及安全的问题请直接咨询有资质的技师。`
