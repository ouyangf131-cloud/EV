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
| `pe_slots` | Parameter Extractor | 槽位提取 | `userinput.query` + 当前会话变量（写进 instruction） | 9 个参数 + `__is_success`、`__reason` | 指令见 system-prompts.md §3 |
| `code_merge_slots` | Code | 合并槽位 | `pe_slots.__is_success`、`pe_slots` 的 9 个新值、9 个会话变量旧值 | 9 个合并后的 String + `fault_query` | 新旧合并：失败/空值保留旧值；不确定类说法统一为「不确定」且不覆盖已确定的旧值；拼接检索词。代码见 §2.1 |
| `va_slots` | Variable Assigner | 保存槽位 | `code_merge_slots` 的 9 个输出 | 写入会话变量 | 操作模式 Overwrite（写入的是合并结果，不会被空值清空） |
| `if_slots` | If-Else | 信息是否齐全 | 会话变量 | 2 条路径 | 条件见 §3 |
| `kr_intake` | Knowledge Retrieval | 问诊清单检索（可选） | `userinput.query` | `result` | 知识库 `ev-knowledge`；可用 metadata 只检索 01 文件 |
| `llm_intake` | LLM | 信息收集 | Context = `kr_intake.result`；会话变量 | `text` | 只问缺失信息，不给结论 |
| `kr_fault` | Knowledge Retrieval | 排查资料检索 | `code_merge_slots.fault_query`（品牌+车型+症状等拼接） | `result` | 知识库 `ev-knowledge`；不用本轮原话，因为多轮时本轮可能只是"海豚，2022 年"这样的补充 |
| `llm_troubleshoot` | LLM | 排查方向 | Context = `kr_fault.result`；会话变量 | `text` | 输出"可能方向/待核实" |
| `kr_knowledge` | Knowledge Retrieval | 知识检索 | `userinput.query` | `result` | 知识库 `ev-knowledge` |
| `llm_knowledge` | LLM | 知识问答（带引用） | Context = `kr_knowledge.result` | `text` | 依据不足时说不知道 |
| `kr_glossary` | Knowledge Retrieval | 术语检索 | `userinput.query` | `result` | 知识库 `ev-glossary` |
| `llm_english` | LLM | 术语+例句+对话 | Context = `kr_glossary.result` | `text` | |
| `llm_refusal` | LLM | 安全拒答模板 | `userinput.query`、`llm_classify.text` | `text` | 处理 unsafe_hv / out_of_scope |
| `ans_intake` / `ans_troubleshoot` / `ans_knowledge` / `ans_english` / `ans_refusal` | Answer | 回复 | 对应 LLM 的 `text` | 回复用户 | 内容只放 `{{#<llm_id>.text#}}` |

共 21 个节点、21 条边（见 `dify/chatflow-design.json`）。

### 2.1 Code 节点「合并槽位」（`code_merge_slots`）

为什么需要：Variable Assigner 对 String 只有 Overwrite / Clear / Set，没有"非空才写"。如果直接把 `pe_slots` 的输出 Overwrite 到会话变量，提取失败（`__is_success=0`）或某一项漏填时，旧值会被空值清空。所以在 `pe_slots` 和 `va_slots` 之间加一个 Code 节点做合并，`va_slots` 再统一 Overwrite 合并结果。

输入变量（共 19 个，名字要和代码参数一致）：

| 输入名 | 来源 |
|------|------|
| `is_success` | `pe_slots.__is_success` |
| `new_brand` … `new_recent_events`（9 个） | `pe_slots` 的同名参数 |
| `old_brand` … `old_recent_events`（9 个） | 同名会话变量 `conversation.xxx` |

输出变量（10 个，类型都选 String）：`brand`、`vehicle_model`、`model_year`、`powertrain`、`mileage`、`power_state`、`symptom`、`warning_info`、`recent_events`，以及 `fault_query`（给 `kr_fault` 做检索词，见 §4）。

合并规则：
1. `__is_success == 0`（提取失败）→ 9 个槽位全部沿用旧值
2. 新值为空（空字符串、None、只有空格/标点、`null`/`None`/`undefined`）→ 保留旧值
3. **不确定类说法统一成「不确定」**：不确定、不知道、未知、unknown（不分大小写）、不清楚、没注意（到）、不记得、说不清、not sure、I don't know、idk、N/A、待确认 等，以及"我也不太清楚呢"这类口语变体。匹配前去掉空格和标点、转小写，并且要**整句匹配**（"不知道为什么开不了"这种症状描述不会被误判）
4. `power_state` 只保留 3 个确定值：`能READY` / `不能READY` / `12V都没电`（"能 ready""进不了READY""READY不亮"等常见写法会先映射成这 3 个）；其他任何值（如"黑屏，车门能开"）一律视为「不确定」，宁可多问一次
5. **「不确定」不能覆盖已确定的旧值**，只能填进原本为空的槽位；确定的新值可以覆盖旧值（包括覆盖旧的「不确定」）
6. 输出 `fault_query` = 品牌 + 车型 + 动力类型 + power_state + 症状 + 仪表提示（跳过空值和「不确定」，用空格连接）

已知局限：用户想主动清空某个槽位（例如换了一台车）时，这个合并逻辑不会清空；建议换车时新开会话。

代码（Python 3）。仓库里的 `dify/code_merge_slots.py` 是同一份代码，`tests/test_code_merge_slots.py` 是离线单元测试（`python3 tests/test_code_merge_slots.py`，只用标准库；测试也会检查本节代码、JSON 里的代码和 `.py` 文件逐字一致）。**这些测试只验证合并逻辑本身，未在 Dify 中运行**；Dify 沙箱是否允许 `import re`、`__is_success` 的实际类型等需要以后实测。

```python
import re

SLOTS = ["brand", "vehicle_model", "model_year", "powertrain", "mileage",
         "power_state", "symptom", "warning_info", "recent_events"]

UNCERTAIN = "不确定"
# power_state 只允许 3 个确定值；下面是常见同义写法（去空格/标点、转小写后整句匹配）
POWER_STATES = {
    "能READY": ["能ready", "能进入ready", "可以ready", "可以进入ready", "ready正常",
                "能正常ready", "可以正常ready", "正常ready", "ready能亮", "ready亮"],
    "不能READY": ["不能ready", "不能进入ready", "进不了ready", "无法ready", "无法进入ready",
                "上不了ready", "ready不亮", "没有ready"],
    "12V都没电": ["12v都没电", "12v没电", "全车没电"],
}

# 表示"不确定/不知道"的说法（去掉空格和标点、转小写后整句匹配）
_UNCERTAIN_WORDS = {
    "不确定", "不太确定", "不知道", "不太知道", "不清楚", "不太清楚", "未知", "不详",
    "没注意", "没注意到", "没留意", "不记得", "记不清", "忘了", "说不清", "不晓得",
    "待确认", "待定", "待核实", "unknown", "unsure", "notsure", "idk",
    "dontknow", "idontknow", "n/a", "na",
}
# 口语变体：如"我也不太清楚呢""没注意到啊"
_UNCERTAIN_RE = re.compile(r"^(我)?(也)?(不太|不|没)(确定|知道|清楚|记得|注意|注意到|留意|晓得)(了|呢|啊|哦|耶)?$")
_EMPTY_WORDS = {"null", "none", "undefined", "nil"}
_STRIP_RE = re.compile(r"[\s。，,\.！!？?~～、（）()\"'“”‘’：:；;]+")


def _clean(v):
    if v is None:
        return ""
    return str(v).strip()


def _key(v):
    return _STRIP_RE.sub("", v).lower()


def _normalize(slot, v):
    """返回 (值, 是否不确定)。空值返回 ("", False)。"""
    v = _clean(v)
    k = _key(v)
    if not k or k in _EMPTY_WORDS:
        return "", False
    if k in _UNCERTAIN_WORDS or _UNCERTAIN_RE.match(k):
        return UNCERTAIN, True
    if slot == "power_state":
        for name, aliases in POWER_STATES.items():
            if k in aliases:
                return name, False
        # 不在枚举里的 power_state 一律视为不确定（宁可再问一次）
        return UNCERTAIN, True
    return v, False


def main(is_success,
         new_brand, new_vehicle_model, new_model_year, new_powertrain, new_mileage,
         new_power_state, new_symptom, new_warning_info, new_recent_events,
         old_brand, old_vehicle_model, old_model_year, old_powertrain, old_mileage,
         old_power_state, old_symptom, old_warning_info, old_recent_events) -> dict:
    args = dict(locals())
    # 提取失败（__is_success == 0）时，不采用任何新值
    failed = _clean(is_success).lower() in ("0", "0.0", "false")
    out = {}
    for k in SLOTS:
        old, old_unsure = _normalize(k, args.get("old_" + k))
        new, new_unsure = _normalize(k, args.get("new_" + k))
        if failed or not new:
            out[k] = old                      # 新值为空/提取失败 → 保留旧值
        elif new_unsure and old and not old_unsure:
            out[k] = old                      # "不确定"不能覆盖已确定的旧值
        else:
            out[k] = new                      # 其余情况用新值（"不确定"只能填空位）
    parts = [out[k] for k in ("brand", "vehicle_model", "powertrain", "power_state",
                              "symptom", "warning_info") if out[k] and out[k] != UNCERTAIN]
    out["fault_query"] = " ".join(parts)      # 供 kr_fault 检索用（NB5）
    return out
```

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
| IF 齐全（handle `complete`） | 对 `brand`、`vehicle_model`、`power_state`、`symptom` 这 4 个会话变量，**每个**都要满足：is not empty **AND** **not contains** `不确定`（共 8 条条件，全部 AND） | `kr_fault` → `llm_troubleshoot` |
| ELSE 缺信息（handle `else`） | 其他 | `kr_intake` → `llm_intake` |

关于「不确定」："不确定"是非空值，如果只判断 is not empty，就会被当成"齐全"而跳过问诊。`code_merge_slots` 已把"不知道/未知/unknown/不清楚/没注意"等说法和 power_state 的非枚举值统一成「不确定」，所以这里只需判断「不确定」一个字面值。本设计选择**只改条件**（非空 **且** 不包含「不确定」），不加追问计数变量：必填项为「不确定」时继续走 `llm_intake`，由问诊节点用可观察的现象（屏幕亮不亮、仪表有没有 READY 字样、能不能挂挡行驶）再问一次。已知局限：如果用户始终答不出，会一直停留在问诊环节，不会给排查方向（这是有意的保守设计）；这时问诊提示词会建议联系品牌售后或有资质的技师现场确认（见 system-prompts.md §4 第 7 条）。

### 3.3 备选：用 Question Classifier 代替「LLM 意图分类 + If-Else」

Dify 官方有 **Question Classifier** 节点：输入变量（通常是用户 query）→ 选模型 → 定义多个 class（class 标题显示在画布上，class 描述给 LLM 看），每个 class 自动成为一条输出路径；还可以写 Instructions 处理边界情况。

| 对比 | LLM + If-Else（本设计默认） | Question Classifier（备选） |
|------|------|------|
| 节点数 | 2 个 | 1 个 |
| 可控性 | 提示词完全自定义，可以写详细的优先级规则 | 通过 class 描述 + Instructions 控制 |
| 调试 | 能直接看到 LLM 输出的标签文本 | 看走了哪个 class |
| 新手难度 | 稍高 | 更低，推荐新手先试 |

若改用 Question Classifier，5 个 class 描述可直接复制 system-prompts.md §2 中的标签定义，并把"高压安全优先"写进 Instructions。

改用 Question Classifier 后没有 `llm_classify.text`：`llm_refusal` 的 SYSTEM 里把 `{{#llm_classify.text#}}` 换成 Question Classifier 的输出变量 `class_name`（官方文档写明 class 名称会作为 `class_name` 暴露给下游），并把 class 标题设为 `unsafe_hv` / `out_of_scope` 等英文标签，这样 §8 情况 A/B 的判断仍然成立。也可以把 `unsafe_hv` 和 `out_of_scope` 分别连到两个拒答 LLM 节点（各自只保留情况 A 或 B）。两种做法都需要在 Dify 中实测。

## 4. Knowledge Retrieval 节点设置建议

依据官方文档：需要设置 **Query Text**（一个文本变量；`kr_knowledge`、`kr_glossary`、`kr_intake` 选 `userinput.query`，`kr_fault` 选 `合并槽位` 的 `fault_query`）、选择知识库、配置 **Retrieval Setting**（Rerank / Weighted Score、Top K、Score Threshold）。输出变量为 `result`。

- Top K：建议从较小值开始（例如 3–5），根据测试调整（**建议值，未经测试**）
- Score Threshold：先关闭，测试后再决定是否开启
- 在 LLM 节点中：**Context** 选该节点的 `result`，并在系统提示词里引用 Context 变量

## 5. Answer 节点

每个分支一个 Answer 节点，内容只放对应 LLM 的输出变量。官方文档说明 Answer 节点按变量就绪顺序流式输出。

## 6. 错误处理（详见 safety-and-errors.md）

LLM 节点支持重试与失败兜底（默认值 / 错误分支 / 备用模型，以当前版本界面为准）。建议所有 LLM 节点设置"默认值"兜底文本：
`抱歉，系统暂时没能生成回答。请稍后再试；涉及安全的问题请直接咨询有资质的技师。`
