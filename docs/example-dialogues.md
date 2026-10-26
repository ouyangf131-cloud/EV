# 三个场景的完整示例对话（Example Dialogues）

> ⚠️ 以下对话是**人工编写的设计示例**，用来说明"助手应该怎么回答"，**不是 Dify 的实际输出**（本 Chatflow 尚未运行）。
> 品牌仅为教学举例；对话中不包含任何品牌的真实故障码定义、规格或手册步骤。教学示例，使用前以现行车厂手册与法规为准。

---

## 场景 1：故障症状 → 先问诊 → 排查方向（fault 分支）

**第 1 轮**

> **用户：** 有台比亚迪的车早上开不了，仪表亮了个黄色的灯。

路由：`llm_classify` → `fault` → `pe_slots`（提取到 brand=BYD 比亚迪，symptom=早上开不了、仪表亮黄灯）→ `code_merge_slots` → `va_slots` → `if_slots`：缺 vehicle_model、power_state → `llm_intake`

> **EV 助手：**
> 我先确认一下：是一台 **BYD（比亚迪）** 的车，早上无法行驶，仪表有黄色指示灯。
> 为了给出靠谱的排查方向，请补充下面几点：
> 1. **具体车型**是什么？（例：海豚 Dolphin / 元 PLUS / 秦 PLUS DM-i）
> 2. 踩刹车按启动后，**仪表能不能显示 READY**（或"OK"/可行驶提示）？（例：能亮 READY 但挂挡不走 / 完全不亮 READY / 屏幕都不亮）
> 3. 是**纯电（BEV）还是插混（PHEV, DM-i）**？
> 4. 黄色灯是什么图案，或者仪表上的**提示文字原文**是什么？（例：一个黄色感叹号 + "请检查……"）
> 5. 最近有没有**涉水、碰撞、维修、或者长时间没开**？
>
> 如果闻到焦糊味、看到冒烟或车泡过水，请先不要再启动车辆，远离车辆并联系品牌售后。

**第 2 轮**

> **用户：** 海豚，2022 年的，纯电，跑了 5 万公里。屏幕能亮，但是 READY 不亮。放了一个多星期没开。黄灯是个电池图案。

路由：`fault` → `pe_slots`（补齐 vehicle_model=海豚 Dolphin、model_year=2022、powertrain=BEV、mileage=5 万公里、power_state=不能READY、warning_info=黄色电池图案、recent_events=停放一周多；没提到的旧值由 `code_merge_slots` 保留）→ `va_slots` → `if_slots`：齐全 → `kr_fault` → `llm_troubleshoot`

> **EV 助手：**
> **【安全提醒】** 下面只包含不接触高压部件的检查；任何高压部件检查只能由有资质的人员按 BYD 官方维修手册进行。
>
> **【我理解的情况】** 2022 年 BYD 海豚（纯电），5 万公里，停放一周多后屏幕能亮但无法进入 READY，仪表有黄色电池图案。
>
> **【可能方向/待核实】**
> 1. 可能方向/待核实：**12V auxiliary battery（12V 低压蓄电池）电量不足**
>    - 依据：《02-ev-basics》提到，车辆唤醒和上高压时控制模块需要低压电，低压电池严重亏电时，即使动力电池电量充足，车辆也可能无法进入 READY；同文还提到长期停放后 12V 低压蓄电池可能出现亏电（一般经验，待核实）。《01-fault-intake》把"长期停放"列为需要询问的最近事件。
>    - 先做的低风险检查：确认 12V 蓄电池是否有亏电迹象；记录仪表提示原文；用诊断仪读取并记录故障码和冻结帧（freeze frame）。
> 2. 可能方向/待核实：**动力电池或电池管理系统（BMS）相关的提示**
>    - 依据：《01-fault-intake》要求记录仪表提示**原文**或图案和颜色，不要凭图案猜含义，以车辆用户手册为准；如已读取故障码，含义必须对照该品牌官方资料。《02-ev-basics》说明 BMS 负责监测电芯电压、温度、电流并保护电池。
>    - 注意：黄色电池图案具体代表什么，**以 BYD 官方用户手册/维修手册为准**，我不做猜测。
> 3. 可能方向/待核实：**其他上电条件未满足（例如高压互锁 HVIL 或绝缘监测相关）**
>    - 依据：《02-ev-basics》说明 HVIL 检测异常时系统可能禁止上高压，绝缘下降时系统会报警或限制功能；《03-safety-hv》说明高压作业只能由经过正规培训、取得相应资质的人员按官方维修手册进行。
>
> **【需要官方资料确认的】**
> - 黄色电池图案的确切含义 → 查车辆用户手册或 BYD 官方售后
> - 诊断仪读到的故障码的含义 → 用原厂或专业诊断仪 + BYD 官方维修资料确认
> - 是否有相关技术通报（TSB）或召回 → 问 BYD 授权服务中心
>
> **【下一步可以告诉我】** 有没有诊断仪读到的故障码？（只要把字符原样告诉我，我会帮你整理要问售后的问题，但不会猜测含义。）
>
> 以上为教学示例，使用前以现行车厂手册与法规为准。

---

## 场景 2：维修知识问答（knowledge 分支，带引用；依据不足时说不知道）

**第 1 轮**

> **用户：** DC-DC converter 是干什么的？为什么 Tesla 那种车 12V 电池没电了也开不了？

路由：`llm_classify` → `knowledge` → `kr_knowledge` → `llm_knowledge`

> **EV 助手：**
> **一句话回答：** DC-DC converter（直流-直流转换器）把高压电池的电转换成低压电，给 12V 低压系统供电、给 12V 蓄电池充电。
>
> - 12V 低压蓄电池（12V auxiliary battery）给控制模块、灯光、门锁等低压系统供电；部分车型使用其他类型的低压电池，以官方资料为准。【来源：02-ev-basics】
> - DC-DC 转换器把高压直流电转换为低压直流电，给低压电器供电并给 12V 蓄电池充电，作用类似燃油车上的发电机（alternator）。【来源：02-ev-basics】
> - 车辆唤醒和上高压时，控制模块需要低压电，所以低压电池严重亏电时，**即使动力电池电量充足，车辆也可能无法进入 READY**。不同车型设计不同，以官方资料为准。【来源：02-ev-basics】
> - 知识库中没有 Tesla 的专门资料；Tesla 车型的具体设计请以 Tesla 官方资料为准。
>
> 以上为教学示例，使用前以现行车厂手册与法规为准。

**第 2 轮**

> **用户：** 那 Model 3 的 DC-DC 输出是多少伏、多少安？

路由：`knowledge` → 检索结果中没有该规格 → `llm_knowledge` 规则 2、3

> **EV 助手：**
> 知识库中没有找到可靠依据，我不知道，也不会猜测具体数值。
> 不同车型、年款的规格可能不同，建议查：
> - Tesla 官方维修资料（Tesla 提供在线服务信息网站，访问方式和地区可用性待核实）
> - Tesla 授权服务中心
> - 有资质的 EV 技师
>
> 以上为教学示例，使用前以现行车厂手册与法规为准。

---

## 场景 3：中文术语 → 英文 + 例句 + 维修场景对话（english 分支）

> **用户：** 「高压互锁」英语怎么说？给我个例句。

路由：`llm_classify` → `english` → `kr_glossary` → `llm_english`

> **EV 助手：**
> **【英文术语】** High Voltage Interlock Loop，缩写 **HVIL** —— 高压互锁（回路）【来源：04-glossary-en】
>
> **【发音提示】** HVIL 通常按字母读：H-V-I-L；interlock 重音在前面：**IN**-ter-lock。
>
> **【例句】**
> 1. The HVIL is a safety circuit in the high voltage system.
>    HVIL 是高压系统里的一个安全回路。
> 2. Only a qualified technician should work on the HVIL.
>    只有有资质的技师才能处理高压互锁相关的工作。
>
> **【维修场景对话】**（地点：澳大利亚一家维修车间 workshop）
> - **Customer:** My Volkswagen ID.4 won't go into READY mode.
>   车主：我的大众 ID.4 进不了 READY 模式。
> - **Service Advisor:** OK. Did you see any warning on the dashboard?
>   服务顾问：好的。仪表上有任何警告吗？
> - **Customer:** Yes, a yellow warning light.
>   车主：有，一个黄色警告灯。
> - **Technician:** I will scan the car first. It may be an HVIL issue, but I need to check the official service information.
>   技师：我先用诊断仪扫描一下。可能和高压互锁有关，但我需要查官方维修资料确认。
> - **Customer:** Can you fix it today?
>   车主：今天能修好吗？
> - **Technician:** I'm not sure yet. I will call you after the diagnosis.
>   技师：还不确定。诊断完我给你打电话。
>
> **【澳洲用法小提示】** 澳洲常说 **workshop**（维修车间）和 **mechanic**（汽修工）；"scan the car" 是口语中"用诊断仪扫描"的常见说法。
>
> 以上为教学示例，使用前以现行车厂手册与法规为准。
