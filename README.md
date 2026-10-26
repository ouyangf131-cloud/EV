# EV —— 新能源汽车维修学习助手（Dify Chatflow 设计稿）

> **一句话说明：这个仓库目前只有「设计文档 + 示例知识库 + 测试用例」，还没有在任何地方部署或运行过 Dify。**
> 以后有电脑/有时间时，按 `docs/deploy-later.md` 和 `dify/import-guide.md` 一步一步搭起来即可。

作者 / Owner：Mike（GitHub: `ouyangf131-cloud`）
文档语言：中文为主，专业术语保留英文（English technical terms kept in English）。

---

## 1. 这个助手是做什么的？（3 个功能）

| # | 功能 | 用户怎么问 | 助手怎么答 |
|---|------|-----------|-----------|
| 1 | **故障症状 → 排查方向** | 「比亚迪海豚仪表亮黄色故障灯，车上不了电」 | 先问清楚必要信息（品牌/车型/年款、里程、能否上电/READY、症状、仪表提示），再给出**有依据的排查方向**，标注「可能方向/待核实」，**不下结论** |
| 2 | **维修知识问答** | 「DC-DC converter 是干什么的？」 | 从知识库检索（Knowledge Retrieval）后回答，并**标出来源**；知识库里没有就直接说「我不知道」 |
| 3 | **中文术语 → 英文** | 「高压互锁 英文怎么说？」 | 给出英文术语 + 简单例句 + 一段简短的维修场景对话（为以后去澳大利亚工作练英语） |

覆盖的示例品牌：Tesla、广汽埃安（GAC Aion）、比亚迪（BYD）、日系（Toyota / Nissan / Honda）、德系（VW ID. / BMW i / Mercedes EQ）。
**所有品牌内容都是一般性教学示例，不编造任何品牌的故障码（DTC）、规格或手册步骤。**

## 2. 现在仓库里有什么？（没有什么？）

**有：**
- 完整的 Chatflow 设计：节点、变量、分支条件、每个 LLM 节点的完整提示词
- 5 份示例知识库文档（可以直接上传到 Dify 知识库）
- 17 条测试用例 + 3 段完整示例对话
- 一个结构化 JSON 设计文件 `dify/chatflow-design.json`

**没有（请注意）：**
- ❌ 没有部署 Dify，没有在本地或云端运行过这个 Chatflow
- ❌ `dify/chatflow-design.json` **不是** Dify 官方 DSL，**不能**直接用「导入应用」导入——需要按 `dify/import-guide.md` 在 Dify 界面里手工搭建（约 30–60 分钟，估计值）
- ❌ 示例知识**不是**任何车厂的正式维修手册

## 3. 10 分钟阅读路径（给新手）

1. （2 分钟）读完本 README
2. （3 分钟）看 `docs/architecture.md` 里的流程图，知道有哪些节点
3. （3 分钟）看 `docs/example-dialogues.md` 三段示例对话，知道助手「应该」怎么回答
4. （2 分钟）看 `docs/deploy-later.md`，了解以后两种部署方式：**Dify Cloud 免费 Sandbox**（推荐新手，不用装任何东西）或 自己用 Docker 部署（需要电脑，不推荐现在做）

## 4. 以后怎么部署？（最短路径）

1. 用电脑浏览器打开 Dify Cloud（https://cloud.dify.ai ），注册免费 Sandbox 账号（免费额度以官网当前说明为准，**需要 Mike 确认**）
2. 配置一个模型供应商（Model Provider）
3. 新建知识库，上传 `knowledge/` 下 5 个 `.md` 文件
4. 新建 **Chatflow** 应用，名字填 `EV`，按 `dify/import-guide.md` 拖节点、粘提示词
5. 用 `docs/test-cases.md` 的问题逐条在预览（Preview）里测试，把实际结果记下来

## 5. 目录

```
EV/
├── README.md                    ← 你在这里
├── NOTICE                       ← 免责声明：示例知识不是官方手册
├── docs/
│   ├── architecture.md          ← 总体架构 + 流程图
│   ├── workflow-nodes.md        ← 每个节点、变量、分支条件
│   ├── system-prompts.md        ← 每个 LLM 节点的完整提示词
│   ├── safety-and-errors.md     ← 安全规则 + 出错时怎么办
│   ├── example-dialogues.md     ← 三个场景各一段完整示例对话
│   ├── deploy-later.md          ← 以后部署（Cloud / Docker），需 Mike 确认
│   └── test-cases.md            ← 17 条测试用例 + 预期行为
├── knowledge/                   ← 上传到 Dify 知识库的示例材料
│   ├── 01-fault-intake.md       ← 故障问诊清单（先问什么）
│   ├── 02-ev-basics.md          ← 电动车基础结构（示例教学材料）
│   ├── 03-safety-hv.md          ← 高压安全原则（不含操作步骤）
│   ├── 04-glossary-en.md        ← 中英术语表 + 例句
│   └── 05-australia-notes.md    ← 澳洲工作/认证「如何核实」框架
└── dify/
    ├── chatflow-design.json     ← 结构化设计（非 DSL）
    └── import-guide.md          ← 在 Dify 界面手工搭建的步骤
```

## 6. 安全底线（助手必须遵守）

- 不编造故障码（DTC）、车辆规格、手册原文
- 没核实的推测一律标注「可能方向/待核实」
- 高压（HV）相关：强调资质、官方维修手册、安全规程；**不提供新手可照做的高压操作步骤**
- 澳洲工作/认证：必须附可核实的来源和日期；不知道就说不知道，并指出该去哪类官方渠道查；**绝不编造分数线**
- 所有知识库样例带水印式声明：**教学示例，使用前以现行车厂手册与法规为准**

## 7. 设计依据

节点名称和字段参考 Dify 官方文档（2026-10-26 查阅）：
- Workflow & Chatflow：https://docs.dify.ai/en/self-host/use-dify/build/workflow-chatflow
- Knowledge Retrieval：https://docs.dify.ai/en/self-host/use-dify/nodes/knowledge-retrieval
- Question Classifier / If-Else / Variable Assigner / Parameter Extractor / LLM / Answer / User Input：https://docs.dify.ai/en/self-host/use-dify/nodes/
- Export and Import Apps：https://docs.dify.ai/en/self-host/use-dify/workspace/export-import-apps

Dify 版本更新很快，实际界面以搭建当天的官方文档为准。
