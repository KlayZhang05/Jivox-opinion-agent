# 下一阶段迭代计划：论坛协作、语义支持、数据库研究与 TikHub 采集

日期：2026-06-08
状态：规划中，尚未实施

## 1. 迭代背景

当前版本已经完成一条可审计的研究链路：

```text
topic
  -> Forum Host 规划
  -> 临时 research subagents 并发检索
  -> 工具输出规范化为 EvidenceRecord
  -> Citation Agent 选择候选引用
  -> ExactQuoteEvaluator 检查原文片段
  -> 生成报告、验证 sidecar 和脱敏 trace
```

但当前 `ExactQuoteEvaluator` 的能力很窄。它验证的是：

> `direct_quote` 的文本是否逐字存在于所引用的 evidence 中。

这个判断更准确地属于 **引用出处验证（quote provenance）**，而不是一般意义上的 **证据语义支持（semantic support）**。它能够防止伪造或改写引用，却不能验证以下有分析价值的 claim：

- 对事实的忠实转述；
- 对多个样本观点的归纳；
- 对不同来源共识与分歧的总结；
- 在明确前提和范围下形成的分析性推断。

因此，下一阶段不再把“原文 1:1 出现”等同于通用 `supported`，而是建立分层验证体系。同时引入通用 `analyst_agent` 和论坛协作 Skill，实现由多个临时 Analyst 实例形成部分报告、Forum Host 根据研究缺口发起后续轮次、最终 Report Agent 在长上下文中综合报告的工作流。`database_researcher` 和 `tikhub_researcher` 则为论坛提供历史证据与有界社交媒体样本。

## 2. 本轮目标

本轮计划包含四个工作流：

1. 实现可通过 Skills 注入的动态论坛协作机制和通用 `analyst_agent`；
2. 将 claim gate 从直接引文验证扩展为语义支持验证；
3. 实现只读的 `database_researcher`；
4. 实现有界采集的 `tikhub_researcher`。

目标架构：

```text
Forum Host + Forum Collaboration Skill
    ↓ dynamic research agenda
Temporary Analyst Instances
    ├─ web tools
    ├─ database tools
    ├─ TikHub tools
    └─ built-in ML model tools (contract only)
    ↓
AnalysisMemo / PartialReport[]
    ↓
Forum Host gap review and optional next round
    ↓
Report Agent long-context synthesis
    ↓
Draft Report + Claim Ledger
    ↓
Quote Provenance / Semantic Support Evaluation
    ↓
Deterministic Assessment Verification
    ↓
Verified Final Report
```

## 3. 明确不在本轮范围内

- 不建设生产级持续监控、定时调度和告警平台；
- 不声称自动判断来源是否真实、权威或独立；
- 不声称 TikHub 样本代表整个平台或社会总体；
- 不实现机器人识别、协同行为检测或传播网络分析；
- 不把所有推理交给单个 LLM 评分；
- 不把论坛工作流硬编码为每次完全相同的角色数量、轮数和任务构成；
- 不在本轮实现内置机器学习模型，只定义其工具契约和结果 provenance；
- 不在没有评测集的情况下宣称语义 evaluator 已达到可靠事实核验水平；
- 不在本计划文档阶段修改任何运行代码。

---

## 4. 工作流一：动态论坛协作与通用 `analyst_agent`

### 4.1 论坛机制的基本原则

下一阶段借鉴有效的论坛式研究流程，但不复制固定角色、固定轮次和固定拓扑。

稳定不变的是协作协议：

```text
Forum Host 提出本轮研究议程
    ↓
按研究目标创建若干临时 Analyst 实例
    ↓
每个 Analyst 使用受约束的 Skills、Tool Set 和数据范围
    ↓
每个 Analyst 生成一份可引用的部分报告
    ↓
Forum Host 汇总部分报告并识别证据缺口、冲突和待追问点
    ↓
必要时创建下一轮 Analyst 实例
    ↓
达到终止条件后交给长上下文 Report Agent 综合
```

可变化的是：

- 每轮 Analyst 实例数量；
- 每个实例的分析目标；
- 注入的 Skill 组合；
- 允许使用的 Tool Set；
- evidence 范围；
- 是否调用数据库、TikHub 或机器学习模型；
- 后续轮次的追问方向。

### 4.2 固定基础角色与动态实例

不允许模型随意发明新的系统级角色 ID。下一阶段在角色注册表中新增一个通用基础角色：

```text
analyst_agent
```

Forum Host 可以创建多个临时实例：

```text
analyst:official_narrative
analyst:public_reaction
analyst:historical_comparison
analyst:conflict_review
```

这些名称是实例任务标签，不是新的权限角色。所有实例仍受 `analyst_agent` 的基础 schema、实例上限和安全边界约束；具体能力由 Forum Host 从预定义 Skill 库和已注册工具中选择。

### 4.3 Forum Collaboration Skill

论坛工作流应作为可注入主 Agent 的 Skill，而不是完全写死在 LangGraph 拓扑中。该 Skill 至少规定：

- 先列出本轮研究问题和已有证据缺口；
- 仅创建能够减少具体缺口的 Analyst 任务；
- 尽量让同轮任务相互独立，以便并发执行；
- 每轮结束后比较各部分报告的共识、冲突和遗漏；
- 后续任务必须来自明确的新问题，不能无理由重复检索；
- 达到证据覆盖、轮次、成本或时间上限时终止；
- 最终只把有 provenance 的部分报告交给 Report Agent。

### 4.4 Analyst Agent 的职责

`analyst_agent` 接收：

- 明确的分析目标；
- 允许使用的 Skill bundle；
- 允许调用的 Tool Set；
- Forum Host 提供的上下文和上一轮问题；
- 本实例可访问的 evidence、数据库结果或社媒样本；
- 输出范围、时间窗口和禁止外推规则。

它可以执行受限的工具循环：

```text
理解目标
  -> 选择并调用工具
  -> 检查结果是否足够
  -> 必要时继续调用允许的工具
  -> 生成部分报告
```

它不能：

- 修改自己的工具权限；
- 访问其他实例未授权的数据；
- 把工具失败包装成事实；
- 把样本结果扩大为总体结论；
- 直接发布最终报告。

### 4.5 内置机器学习模型工具契约

Analyst 的 Tool Set 除检索工具外，可以包含项目内置机器学习模型，但本轮只定义契约，不实现模型。候选工具包括：

```text
sentiment_classify
stance_classify
topic_cluster
semantic_deduplicate
entity_extract
engagement_summarize
```

机器学习工具输出必须保存：

- 模型 ID 和版本；
- 输入 evidence IDs；
- 运行参数；
- 标签定义；
- 输出分数或类别；
- 运行时间；
- 失败信息；
- 是否经过人工校准。

模型结果属于 `DerivedEvidence` 或 `AnalysisArtifact`，不能伪装成原始用户评论或网页原文。

### 4.6 部分报告契约

Analyst 不应逐条调用模型生成孤立 claim，而应一次生成一个结构化 `AnalysisMemo`：

```text
memo_id
analysis_goal
executive_summary
sections[]
claim_ledger[]
evidence_ids[]
derived_artifact_ids[]
limitations[]
open_questions[]
conflicts[]
```

其中：

- `executive_summary` 和 `sections` 承载连贯分析；
- `claim_ledger` 批量列出报告中的可验证主张；
- 每个 ledger entry 指向正文位置、claim type、scope 和 evidence IDs；
- `limitations` 明确本实例不能得出的结论；
- `open_questions` 供 Forum Host 决定下一轮任务；
- `conflicts` 记录来源或分析结果之间的分歧。

因此，claim 不再是写作流程的最小调用单位，而是部分报告的结构化验证索引。

### 4.7 多轮论坛控制

Forum Host 每轮接收：

```text
AnalysisMemo[]
+ 当前 evidence inventory
+ claim verification summary
+ 预算与轮次状态
```

然后选择：

```text
continue: 创建新的 Analyst tasks
repair: 要求某个方向补充证据或缩小 scope
challenge: 创建反方/冲突检查任务
finish: 交给 Report Agent
```

必须设置硬终止条件：

- 最大论坛轮数；
- 最大 Analyst 实例数；
- 最大工具调用数；
- token、时间或金额预算；
- 连续两轮没有新增有效 evidence；
- 剩余问题均被标记为 `indeterminate` 或超出范围。

### 4.8 Report Agent 的新职责

最终 Report Agent 接收：

- 所有通过基本 schema 检查的 AnalysisMemo；
- memo 对应的 evidence 和 derived artifacts；
- claim ledger 与验证状态；
- Forum Host 的最终综合要求；
- 冲突、局限和 unresolved questions。

Report Agent 可以进行长上下文综合、章节组织和跨 memo 比较，不再只负责 claim ID 排序。但它必须输出：

```text
DraftReport
    ├─ narrative sections
    ├─ final claim ledger
    ├─ source/memo references
    ├─ limitations
    └─ unresolved disagreements
```

最终报告中的新主张必须进入 final claim ledger；不能只藏在过渡句或标题中绕过验证。

### 4.9 工作流一验收标准

- 新增固定基础角色 `analyst_agent`；
- Forum Host 能动态创建不同目标、Skill bundle 和 Tool Set 的 Analyst 实例；
- 论坛协议通过 Skill 注入，而非固定死每轮拓扑；
- 同轮 Analyst 可以并发；
- Forum Host 能依据 memo 的缺口、冲突和开放问题发起下一轮；
- Analyst 输出结构化 AnalysisMemo，而不是逐条孤立 claim；
- claim ledger 能定位到 memo 正文中的主张；
- ML 工具只有契约，输出明确标记为 derived artifact；
- Report Agent 能综合多份 memo，但新增主张必须进入 final claim ledger；
- 存在明确的轮次、成本和无新增证据终止条件。

---

## 5. 工作流二：从引用出处验证扩展到语义支持

### 5.1 重新定义验证层次

下一版本应明确区分五层判断：

| 层次 | 问题 | 判断方向 |
|---|---|---|
| Citation existence | 引用的 evidence 是否存在？ | ID -> Record |
| Quote provenance | 引文是否来自该 evidence 的连续原文？ | Evidence -> Quote |
| Semantic support | evidence 的语义是否支持 claim？ | Evidence -> Claim |
| Factual validity | claim 是否符合现实世界事实？ | World -> Claim |
| Representativeness | 样本能否支持更大总体结论？ | Sample -> Population |

本轮重点实现前 3 层。后两层只保留接口和研究说明，不作为当前系统保证。

### 5.2 调整 evaluator 命名和职责

当前 `ExactQuoteEvaluator` 应在后续代码迭代中收窄为类似：

```text
ExactQuoteProvenanceEvaluator
```

它只负责：

- 验证 `direct_quote` 是 cited evidence 中的连续原文；
- 验证字符 offset 与原文一致；
- 返回引用出处验证结果。

新的：

```text
SemanticSupportEvaluator
```

负责判断：

> 在 claim 声明的 `claim_type` 和 `scope` 内，所引用 evidence 是否在语义上支持该 claim。

### 5.3 面向部分报告的批量验证链路

```text
AnalysisMemo / DraftReport
    ↓ claim ledger extraction and schema validation
ClaimBatch[]
    ↓
SemanticSupportEvaluator
    ↓
SupportAssessmentBatch
    ↓
Deterministic Verifier
    ↓
accepted claims / rejected claims / repair request
```

Analyst 和 Report Agent 可以生成新表述，但必须满足：

- 每个 ledger claim 只包含一个可独立验证的主张；
- 明确声明 `claim_type`；
- 明确列出 `evidence_ids`；
- 明确声明平台、时间窗口和样本范围；
- 能定位回 memo 或最终报告中的正文位置；
- 不把局部样本表述为总体舆论；
- 数量、比例和比较关系必须结构化表达，不能只藏在自然语言中。

验证以批为单位执行，避免“每写一句就单独调用一次 evaluator”的低效率做法。系统可以先按 evidence bundle、claim type 和 memo 分组，再批量评价，并对失败项定向 repair。

### 5.4 Claim 类型的分阶段支持

#### `direct_quote`

验证方式：

```text
Exact quote provenance + evidence existence
```

准入要求：

- quote 是原文连续 span；
- offset 有效；
- evidence ID 存在；
- scope 与来源 metadata 一致。

#### `factual_statement`

示例：

> 官方公告称，该服务将在 6 月 10 日暂停维护。

验证方式：

- evaluator 判断 cited evidence 是否蕴含该陈述；
- 返回支持该 claim 的原文 span；
- verifier 检查 span 确实存在；
- 时间、主体、否定词、数量等结构化要素必须一致；
- 若来源之间存在直接冲突，不能返回无条件 `supported`。

首个版本可使用结构化 LLM evaluator；后续可增加 NLI 模型作为第二判断器。

#### `opinion_summary`

示例：

> 在本次收集的 30 条评论中，价格是最常见的负面关注点。

验证方式不能只靠一句 LLM verdict，而应拆成：

1. 每条 evidence 与主题的相关性分类；
2. 观点标签或主题标签；
3. 支持、反对、中立或无关分类；
4. 程序确定性统计样本数量；
5. 检查 claim 中的数量、比较级和 scope；
6. evaluator 判断自然语言概括是否忠实于结构化统计结果。

最终报告必须同时展示：

- 样本数量；
- 数据来源；
- 时间窗口；
- 标签定义；
- 支持该总结的 evidence IDs；
- 是否存在明显反例或分歧。

#### `analytic_inference`

示例：

> 用户争议可能主要来自价格上涨与功能增益之间的不匹配。

此类 claim 风险最高。第一阶段默认：

```text
indeterminate
```

只有配置专门的推理 evaluator 后才允许验证。未来 evaluator 至少应返回：

- 明确前提；
- 推理步骤摘要；
- 支持证据；
- 反证或替代解释；
- scope；
- 不确定性原因。

### 5.5 SemanticSupportEvaluator 输出

建议扩展 `SupportAssessment`：

```json
{
  "claim_id": "claim-001",
  "claim_type": "factual_statement",
  "verdict": "supported",
  "reason": "The cited notice explicitly states the maintenance date.",
  "scope": {
    "platform": "official_website",
    "time_window": {
      "start": "2026-06-08",
      "end": "2026-06-08"
    },
    "sample": "single official notice"
  },
  "supporting_spans": [
    {
      "evidence_id": "ev-001",
      "quote": "服务将于6月10日暂停维护。"
    }
  ],
  "contradicting_spans": [],
  "evidence_judgements": [
    {
      "evidence_id": "ev-001",
      "relation": "entails"
    }
  ],
  "evaluator": "semantic_support_llm",
  "evaluator_version": "1.0"
}
```

`relation` 初始值可以限定为：

```text
entails
contradicts
relevant_but_insufficient
irrelevant
```

### 5.6 谁决定 `supported`

后续语义版本中应明确：

1. `SemanticSupportEvaluator` 根据 evidence 提出语义 verdict；
2. `verify_claim_support()` 对 verdict 做确定性审查；
3. release policy 决定 claim 是否进入报告。

确定性 verifier 至少检查：

- assessment 的 claim ID、claim type 和 scope 是否匹配；
- evaluator 只能引用 claim 已声明的 evidence；
- supporting/contradicting span 是否真实存在于 evidence；
- 数量与样本字段是否能由程序重新计算；
- `supported` 是否包含有效 supporting evidence；
- 是否存在未处理的 contradiction；
- evaluator 输出是否符合 schema；
- evaluator 异常、超时或格式错误是否转为 `indeterminate`。

因此准确口径是：

> 语义 evaluator 判断证据与 claim 的语义关系，确定性 verifier 判断这个结果是否满足系统准入条件。

### 5.7 HanLP 在新链路中的位置

HanLP 可用于：

- 中文句子边界检测；
- 为 evaluator 提供候选 supporting spans；
- 降低长 evidence 的输入长度；
- 保留句子与原始字符 offset 的映射。

链路：

```text
EvidenceRecord.content
    ↓
HanLP sentence boundary detection
    ↓
程序按原始 offset 截取 span
    ↓
SourceSpanCandidate[]
```

HanLP 不负责：

- 生成 evidence ID；
- 判断 claim 是否 supported；
- 修改原文；
- 判断来源真实性；
- 写报告。

候选片段必须保存：

```text
candidate_id
evidence_id
char_start
char_end
text
sentence_index
```

并满足：

```python
evidence.content[char_start:char_end] == candidate.text
```

### 5.8 防止 evaluator 成为新的幻觉源

必须保留以下约束：

- evaluator 只能看到 claim 引用的 evidence bundle；
- evidence 内容作为数据输入，而不是可执行指令；
- evaluator 不能检索新来源；
- evaluator 不能修改 claim；
- evaluator 返回的 quote 必须回到 evidence 原文校验；
- evaluator 不能引用 bundle 外的 evidence；
- verdict 不能只依赖未校准的数字置信度；
- evaluator 失败时必须 fail closed；
- trace 记录 evaluator 类型、版本、耗时和 verdict，但不保存隐藏推理。

### 5.9 语义支持评测集

在上线语义 gate 前，建立小型人工标注集，至少覆盖：

- 直接蕴含；
- 忠实改写；
- 主体偷换；
- 时间范围扩大；
- 数量夸大；
- 否定词反转；
- 相关但不足；
- 多证据联合支持；
- 来源冲突；
- 样本总结；
- 总体化误表述；
- 分析性过度推断；
- evidence 内的 prompt injection 文本。

评测指标：

- supported precision；
- unsupported/indeterminate 召回率；
- contradiction detection recall；
- span grounding accuracy；
- scope violation detection；
- malformed-output rejection rate；
- evaluator 运行成本和延迟。

首要目标是降低错误放行，而不是提高报告生成率。

### 5.10 工作流二验收标准

- `direct_quote` 与 semantic support 的概念和 API 分离；
- `factual_statement` 可以基于语义蕴含进入报告；
- `opinion_summary` 必须附带可重算的样本统计；
- `analytic_inference` 在 evaluator 未配置时继续 `indeterminate`；
- evaluator 不能引用未声明 evidence；
- supporting span 必须存在于原文；
- scope 扩大、数量夸大和否定反转被拒绝；
- 任一 evaluator 故障均不生成不合格报告；
- 验证 sidecar 保存完整的结构化 assessment。

---

## 6. 工作流三：实现 `database_researcher`

### 6.1 角色目标

`database_researcher` 用于检索已经采集和验证过的本地材料：

- 历史 EvidenceRecord；
- 历史研究运行；
- 历史 report verification sidecar；
- 已验证 claim；
- 来源与时间 metadata。

它不能把历史报告中的自然语言直接当成一手 evidence。

### 6.2 首期技术路线

采用保守的只读检索方案：

```text
JSONL / verification artifacts
    ↓ ingestion/index job
SQLite
    ├─ evidence table
    ├─ claims table
    ├─ runs table
    └─ FTS5 text index
```

首期优先 SQLite + FTS5，不立即引入向量数据库，原因是：

- 数据规模仍然有限；
- 关键词、时间、平台和来源过滤容易解释；
- 便于本地测试与审计；
- 不增加 embedding 模型和索引一致性问题；
- 后续可以在相同 repository interface 下增加 hybrid retrieval。

### 6.3 工具接口

#### `search_evidence`

输入建议：

```json
{
  "query": "价格争议",
  "platforms": ["weibo"],
  "from_time": "2026-06-01",
  "to_time": "2026-06-08",
  "source_types": ["tikhub_search", "web_search"],
  "limit": 20
}
```

输出：

- evidence ID；
- title/summary；
- source metadata；
- matched text snippets；
- timestamp；
- relevance information；
- run ID。

#### `read_evidence`

输入：

```json
{
  "evidence_ids": ["ev-001", "ev-002"]
}
```

输出完整、只读的 EvidenceRecord。

### 6.4 数据一致性原则

- 数据库只索引已有 evidence，不重新发明 evidence ID；
- 查询结果必须保留原始 provenance；
- 历史报告只能作为检索线索；
- 最终 claim 仍需回到原始 evidence 验证；
- 数据库中的 snippet 不能替代完整 evidence；
- 删除或重建索引不能改变 evidence identity；
- tool output 需要标明索引版本和检索时间。

### 6.5 Research Agent 工作方式

```text
Forum Host
    ↓
ResearchTask(role=database_researcher)
    ↓
search_evidence
    ↓
read_evidence
    ↓
SubagentResult + existing evidence IDs
```

数据库研究结果不应再次写成“新 evidence”。它应引用既有 evidence ID，避免同一来源因重复检索产生多个身份。

### 6.6 边界情况

- 数据库为空；
- FTS 查询无结果；
- evidence ID 在索引中存在但原始记录缺失；
- 同一 evidence 被多个历史 run 使用；
- 时间格式不一致；
- 查询命中历史报告，但无法回溯原始 evidence；
- 索引版本过旧；
- 用户查询包含 SQL 特殊字符；
- 超大结果集；
- 多个来源内容高度重复。

### 6.7 工作流三验收标准

- `database_researcher` 可以被 Forum Host 选择；
- 仅在数据库工具 adapter 已注册时才可执行；
- 支持关键词、时间、平台和来源类型过滤；
- 返回既有 evidence ID，不复制为新 evidence；
- 历史 report claim 必须可追溯到原始 evidence；
- SQL 参数化，无字符串拼接查询；
- 无结果、缺失记录和索引过期均有结构化错误；
- fake adapter 与真实本地 SQLite adapter 均有测试。

---

## 7. 工作流四：实现 `tikhub_researcher`

### 7.1 角色目标

`tikhub_researcher` 负责通过 TikHub API 采集有界社交媒体样本，为后续观点归纳提供结构化 EvidenceRecord。

它不是“全网舆情采集器”，首期必须要求明确：

- 平台；
- query 或目标对象；
- 时间窗口；
- 最大页数；
- 最大记录数；
- 排序方式；
- 采样说明。

### 7.2 工具接口

建议保留统一工具名：

```text
tikhub_search
```

输入示例：

```json
{
  "platform": "douyin",
  "query": "事件关键词",
  "from_time": "2026-06-01T00:00:00+08:00",
  "to_time": "2026-06-08T23:59:59+08:00",
  "max_pages": 3,
  "max_records": 100,
  "sort": "time"
}
```

输出统一为平台无关的 SocialSearchOutput。

### 7.3 社媒 EvidenceRecord

除通用字段外，metadata 至少保留：

```text
platform
post_id
content_type
author_id
author_name
published_at
permalink
engagement snapshot
query
collection_time
page/cursor
sample_rank
provider_request_id
raw_record_hash
```

互动量只能表述为“采集时快照”，不能被当作永久值。

### 7.4 Evidence identity

社媒 evidence ID 应优先基于稳定平台身份：

```text
platform + post_id + content_type
```

同时保存内容哈希和采集时间。

需要区分：

- 同一帖子内容编辑；
- 同一帖子互动量变化；
- 转发/转载与原帖；
- 评论与主帖；
- 视频正文、标题、字幕和评论。

首期策略建议：

- 帖子 identity 保持稳定；
- 内容版本保存 `content_hash`；
- engagement 作为采集快照；
- 原帖和评论分别成为 evidence；
- 不因点赞数变化生成新的 post identity。

### 7.5 有界采集和成本控制

程序必须强制：

- 最大页数；
- 最大记录数；
- 请求超时；
- 速率限制；
- 重试上限；
- cursor 循环检测；
- 响应体大小限制；
- 空 query 拒绝；
- 时间范围上限；
- 单次 research task 成本记录。

模型不能覆盖这些硬限制。

### 7.6 数据规范化

TikHub adapter 只负责：

```text
API payload -> typed provider output
```

统一 normalizer 负责：

```text
typed provider output -> EvidenceRecord
```

Provider 原始 metadata 必须放在：

```text
metadata.provider_metadata
```

不能覆盖可信字段：

- `task_id`
- `role_id`
- `query`
- `source_type`
- `source_name`
- `content_truncated`
- `collection_time`

### 7.7 与语义支持的结合

TikHub 数据进入 `opinion_summary` 前，应先形成明确样本清单：

```json
{
  "platform": "douyin",
  "query": "事件关键词",
  "time_window": {
    "start": "2026-06-01",
    "end": "2026-06-08"
  },
  "collected": 100,
  "usable": 82,
  "excluded": 18,
  "exclusion_reasons": {
    "duplicate": 8,
    "empty": 4,
    "irrelevant": 6
  }
}
```

报告只能表述：

> 在本次按指定 query 和时间窗口收集的样本中……

不能直接表述：

> 网民普遍认为……

### 7.8 边界情况

- API 返回空页；
- cursor 重复；
- 记录缺少 post ID；
- 已删除或不可访问内容；
- 内容编辑；
- 重复转发；
- 评论文本为空；
- 时间戳时区不明确；
- engagement 字段缺失；
- API 字段版本变化；
- 限流、超时和部分页失败；
- query 结果排序机制不透明；
- 平台搜索结果本身存在推荐偏差。

### 7.9 工作流四验收标准

- TikHub 配置完整时才注册 adapter；
- 配置缺失或只配置一半时 fail closed；
- `tikhub_researcher` 只能调用其白名单工具；
- 有明确采集上限和时间范围；
- 记录被规范化为统一 EvidenceRecord；
- 稳定 post identity 与内容版本分离；
- engagement 标明采集时间；
- pagination、限流、重复和部分失败有测试；
- 所有观点总结保留 sample scope；
- 不把平台搜索样本表述为总体舆论。

---

## 8. 四个工作流的集成顺序

### 阶段 A：实现论坛协议与 Analyst 契约

先实现：

```text
Forum Collaboration Skill
analyst_agent
AnalysisMemo
dynamic Skill/Tool assignment
round limits and termination policy
```

先让多个 Analyst 能够形成可追踪的部分报告，但暂不允许未验证内容进入最终发布报告。

### 阶段 B：修正验证语义

先拆分：

```text
quote provenance
semantic support
```

并修正文档、类型和测试口径。

原因：如果不先纠正 `supported` 的含义，后续数据库和 TikHub 提供更多数据，也只会放大错误抽象。

### 阶段 C：实现 SemanticSupportEvaluator 基线

优先支持：

1. `direct_quote`
2. `factual_statement`
3. `opinion_summary`

`analytic_inference` 继续默认 `indeterminate`。

### 阶段 D：实现 `database_researcher`

先让系统能复用历史 evidence，为语义 evaluator 建立可重复测试数据和跨运行检索能力。

### 阶段 E：实现 `tikhub_researcher`

再接入真实社媒样本，并严格保留采样边界。

### 阶段 F：端到端联合验证

目标示例：

```text
Forum Host
  -> 第一轮多个 Analyst: 官方来源、历史证据、社媒样本
  -> AnalysisMemo[]
  -> Forum Host: 识别冲突和证据缺口
  -> 后续轮 Analyst: 补证、反方检查、专题深挖
  -> Report Agent: 长上下文综合
  -> DraftReport + final claim ledger
  -> Batch Semantic Support Gate
  -> Verified Final Report
```

---

## 9. 测试计划

### 9.1 论坛协作与 Analyst

- Forum Host 只能选择预定义 Skill 和已注册工具；
- 同轮 Analyst 实例并发执行；
- 不同实例可以获得不同分析目标和 Tool Set；
- AnalysisMemo schema、正文位置和 claim ledger 对应关系有效；
- 下一轮任务必须对应 open question、conflict 或证据缺口；
- 达到轮次、成本或无新增证据条件时终止；
- Report Agent 新增的主张必须进入 final claim ledger；
- ML 工具输出被标记为 derived artifact，不能伪装成原始 evidence。

### 9.2 语义支持

- 忠实改写通过；
- 关键词重叠但语义不支持时拒绝；
- 否定反转拒绝；
- 主体、时间和数量偷换拒绝；
- supporting span 不存在时拒绝；
- bundle 外 evidence 引用拒绝；
- evaluator timeout/exception 转为 `indeterminate`；
- opinion summary 的程序统计与 claim 不一致时拒绝；
- scope 从单平台扩大到公众总体时拒绝；
- conflicting evidence 未处理时拒绝。

### 9.3 Database Researcher

- FTS 检索；
- 过滤器组合；
- SQL 注入输入；
- 空数据库；
- 缺失原始 evidence；
- 索引重建后 evidence ID 不变；
- 历史报告不可替代原始 evidence；
- Tool Set 权限。

### 9.4 TikHub Researcher

- 正常分页；
- cursor 循环；
- 速率限制；
- 部分页失败；
- duplicate post；
- 缺失字段；
- 内容编辑；
- engagement snapshot；
- 最大记录数和时间窗口；
- provider metadata 不能覆盖 trusted provenance；
- sample scope 保留。

### 9.5 端到端

- Forum Host 能按研究缺口组织多轮 Analyst；
- Analyst 能按实例配置使用 web、database、TikHub 和 ML 契约工具；
- 同轮多实例并发执行；
- evidence 合并后保持稳定 identity；
- 多份 AnalysisMemo 被长上下文 Report Agent 综合；
- final claim ledger 批量验证后进入报告；
- 任一关键 claim 不通过时报告 fail closed；
- sidecar 能解释每个 claim 为什么通过或拒绝；
- trace 不泄露 API key、Authorization、Prompt 或隐藏推理。

---

## 10. 主要风险

| 风险 | 处理原则 |
|---|---|
| Semantic evaluator 自身幻觉 | 限定 evidence bundle、结构化输出、span 回查、fail closed |
| 论坛轮次失控或重复研究 | 明确缺口驱动、轮次/预算上限和无新增证据终止 |
| Analyst 部分报告引入未追踪主张 | 强制 claim ledger 与正文位置映射 |
| Report Agent 在综合时新增隐含事实 | final claim ledger 全量覆盖并在发布前批量验证 |
| ML 输出被误当成原始事实 | 使用 DerivedEvidence/AnalysisArtifact 类型并保存模型 provenance |
| LLM 对“支持”判断不稳定 | 建立人工评测集，版本化 evaluator，记录回归指标 |
| Opinion summary 越过样本范围 | scope 必填，数量由程序重算 |
| TikHub 样本偏差 | 保存 query、时间、排序、页数和排除记录 |
| 历史报告污染新研究 | 报告只作线索，最终回到原始 evidence |
| 多来源重复导致虚假共识 | 后续增加 canonical URL、转载链和近重复检测 |
| API 字段变化 | typed adapter、版本测试、未知字段隔离 |
| 成本与延迟上升 | 上限、缓存、批处理和 evaluator 分级 |

## 11. 计划完成后的准确项目口径

完成本轮后可以表述为：

> Forum Host 通过可配置的论坛协作 Skill，按证据缺口动态创建多个通用 Analyst 实例；各 Analyst 使用受限工具和可选机器学习模型产出带 claim ledger 的部分报告，Forum Host 可据此发起后续补证或冲突检查。最终 Report Agent 在长上下文中综合多份部分报告，语义 evaluator 与确定性 verifier 再批量检查最终主张的证据支持、原文 span、scope 和样本统计，只有满足准入条件的内容才发布。

仍然不能表述为：

- 系统能够自动判断一切事实真假；
- 社媒样本代表全部公众；
- 所有分析性推断都已可靠验证；
- 已达到生产级持续舆情监控能力。

## 12. 预期交付物

后续真正实施时，预期新增或修改：

- semantic support evaluator 协议与 adapter；
- quote provenance evaluator；
- `analyst_agent` 固定基础角色；
- Forum Collaboration Skill；
- AnalysisMemo、partial report 和 final claim ledger schema；
- 多轮 forum state、终止策略与预算控制；
- 支持动态 Skill bundle 和 Tool Set 的 Analyst 实例；
- 长上下文 Report Agent 综合契约；
- 内置机器学习模型工具协议和 DerivedEvidence 类型；
- HanLP source-span splitter；
- scope-aware deterministic verifier；
- SQLite/FTS evidence repository；
- `database_researcher` 工具 adapter；
- TikHub typed client、normalizer 与 bounded collector；
- evaluator benchmark fixtures；
- 三类 researcher 的 fake adapters；
- 端到端测试；
- README、面试手册和真实 smoke verification 更新。

本文件只定义迭代路线，不代表上述能力已经实现。
