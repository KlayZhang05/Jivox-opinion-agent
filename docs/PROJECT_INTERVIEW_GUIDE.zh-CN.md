# Personal Opinion Agent 项目知识与升学面试手册

> 面向 AI 相关研究生升学面试的项目学习材料
> 项目当前主线：基于 LangGraph 的、证据约束的有界舆情研究智能体
> 文档依据：当前源码、测试、设计规格、真实服务冒烟记录与 Git 历史

## 0. 如何使用这份手册

这不是简历 bullet 集合，也不是营销文案。它有三个用途：

1. 帮助项目作者真正理解自己写进 GitHub 的系统；
2. 帮助回答老师从基础概念一路追问到实现细节的问题；
3. 明确项目的证据边界，防止把“代码里预留了接口”说成“已经实现了生产能力”。

建议按以下顺序复习：

1. 先读“1. 一页心智模型”，建立整体图景；
2. 再读“4. 基础知识”，补齐 Agent、LangGraph、证据与验证概念；
3. 然后沿“5. 完整运行流程”逐文件看代码；
4. 重点掌握“18. 具体困难与修复”和“20. 边界情况”；
5. 最后用“24. 面试题”和“25. 口述框架”进行口头复述。

### 0.1 能力状态标签

全文使用以下五种状态。面试时也应主动按这五类表述。

| 标签 | 含义 |
|---|---|
| **[已实现并测试]** | 当前源码中存在实现，并有确定性测试覆盖 |
| **[真实集成验证]** | 除测试外，还使用真实 LLM 与搜索服务完成过一次记录在案的冒烟运行 |
| **[仅定义契约]** | 角色、Schema、Tool ID 或扩展点已经定义，但真实生产适配器没有实现 |
| **[历史原型]** | 仓库中保留的早期功能，不属于当前主动项目主线 |
| **[未来工作]** | 当前没有实现，不应作为现有能力陈述 |

“设计文档写过”“Prompt 中要求过”和“模型偶尔能做到”都不等于 **[已实现并测试]**。

---

## 1. 一页心智模型

### 1.1 一句话定位

Personal Opinion Agent 当前不是完整的舆情监控平台，而是一个适合 GitHub 和升学面试审查的 **有界证据研究切片**：它让一个 Forum Host 将主题拆成若干独立任务，使用 LangGraph 并发启动固定角色的临时 LLM 实例，通过角色授权工具获得可追溯证据，再经过确定性的直接引文支持门禁，最后生成报告、验证 sidecar 和脱敏执行轨迹。

### 1.2 它解决的核心问题

普通 LLM 舆情报告可能出现三类混淆：

1. **来源存在不等于内容支持。** URL 真实，不代表报告中的评论真实出现过。
2. **模型说“我查过”不等于工具真的执行过。** 必须由程序掌握工具调用和证据写入。
3. **文本上有支持不等于事实为真。** 一条来源中的原文可以被准确引用，但来源本身仍可能错误、偏颇或不具代表性。

本项目当前重点解决前两类，并明确不宣称已经解决第三类。

### 1.3 主路径

```text
用户主题
  -> Forum Host 生成结构化 ResearchPlan
  -> LangGraph Send 动态 fan-out
       -> 临时 query_agent 实例 A
       -> 临时 query_agent 实例 B
       -> 其他已安装工具适配器对应的固定研究角色
  -> 每个 worker 先规划 Tool Calls
  -> 程序校验权限并真实执行工具
  -> 工具结果规范化为稳定 Evidence Records
  -> worker 只能使用程序给出的 Evidence IDs 做总结
  -> reducer fan-in 合并 worker 结果、证据、轨迹和错误
  -> 程序从证据中生成 deterministic quote candidates
  -> Citation Agent 只选择 candidate_id
  -> 程序物化 direct_quote ClaimInput
  -> ExactQuoteEvaluator + deterministic verifier
  -> Report Writer 只排列已验证 claim_id
  -> 程序确定性渲染 Markdown
  -> evidence.jsonl + report.md
     + report_verification.json + trace.json
```

### 1.4 四个关键设计句

1. **角色固定，实例临时。** Forum Host 可以决定本轮开几个预定义角色实例，但不能发明新角色。
2. **模型提议，程序执行。** 模型可以提议工具调用，但工具权限、参数验证、执行和证据 ID 都由确定性代码掌握。
3. **模型选择，引文不由模型复制。** Citation Agent 只选择程序生成的候选 ID，不能自己抄写、改写或拼接引文。
4. **只有明确通过才输出。** 缺失、格式错误、未知 ID、unsupported、contradicted、indeterminate 或 evaluator 故障都会阻止报告生成。

### 1.5 当前真正实现到哪里

**[已实现并测试]**

- 七种固定角色和不可变角色注册表；
- 角色绑定 Skills、Tool Set、Schema 和实例上限；
- LangGraph `StateGraph`、`Send` 动态 fan-out、reducer fan-in；
- 真实异步 worker LLM 调用，不是在一个 Prompt 里模拟多角色；
- 两阶段 worker：工具计划与证据受限总结；
- 工具权限校验、Pydantic 参数校验和类型化错误；
- 证据规范化、稳定 ID、JSONL 存储；
- deterministic quote candidate、Citation Agent ID 选择；
- `ClaimInput`、四种 `claim_type`、`scope`；
- `ExactQuoteEvaluator` 与 fail-closed 验证；
- 确定性报告、验证 sidecar、脱敏 trace；
- fake adapter 离线全链路和完整测试。

**[真实集成验证]**

- 一次真实 OpenAI-compatible LLM + Anspire-compatible 搜索运行；
- 三个 `query_agent` 的真实模型调用时间区间发生重叠；
- 该次运行收集 23 条证据，生成 1 条通过 exact quote gate 的 claim；
- 记录见 `docs/verification/2026-06-07-real-provider-smoke.md`。

**[仅定义契约]**

- `database_researcher` 的生产检索适配器；
- `multimedia_researcher` 的生产媒体分析适配器；
- `tikhub_researcher` 的 TikHub 工具适配器；
- 非直接引文的语义支持 evaluator。

**[历史原型]**

- `brief`：确定性样例简报；
- `conversation`：有界脚本会话；
- 独立 `report` 命令：从已有 evidence/claims 生成 gated report。

**[未来工作]**

- 定时监控、持续增量采集、多轮 gap-driven research；
- 来源可信度、独立性、代表性、机器人与协同行为分析；
- 向量数据库、checkpoint/replay、生产多媒体和 TikHub 管线；
- 前端、分布式队列、成本预算器与系统化评测集。

---

## 2. 从个人舆情愿景到有界研究切片

### 2.1 原始个人需求

项目最初的动机不是“做一个更会刷热搜的应用”，而是把 LLM 作为比社交媒体更干净的信息入口。

传统报纸和社论提供了对公共事件的有限入口。社交媒体扩大了信息供给，但也带来：

- 信息过载；
- 无关、低质量和重复内容；
- 无限滚动导致的时间消耗；
- 情绪性内容被算法放大；
- 用户在兴奋、恐慌或群体立场中失去独立判断。

原始产品愿景强调“精神卫生”：

- 默认提供低刺激、低成本、模块化简报；
- 只有用户主动要求时才进入深度研究；
- 深入阶段应呈现多个角度和证据；
- 会话有时间与话题边界；
- 模型可以反思和批评用户，而不是一味迎合；
- 数据源可扩展到新闻、社媒、报告和多模态记录。

原始愿景可以分成三条产品线：

1. **计划式简报**：按可变计划自动采集公开信息，以很低的边际成本生成模块化简报；
2. **有界交谈**：用户主动深入时，开启有时间、话题和原则边界的对话，模型可以搜索、引用既有 evidence，也可以向用户提问或反驳；
3. **舆情分析报告**：多个特化角色协作，但所有评论、来源和结论必须经过可追溯证据与支持检查。

这部分记录在：

- `docs/superpowers/specs/2026-06-05-personal-opinion-agent-design.md`
- `docs/superpowers/plans/2026-06-05-personal-opinion-agent-implementation.md`

### 2.2 原始愿景为什么过大

一个完整个人舆情产品同时包含：

- 调度与持续采集；
- 多源数据连接器；
- 去重、聚类、事件演化；
- 简报；
- 有界对话；
- 检索与长期记忆；
- 多模态理解；
- 舆情与立场分析；
- 报告生成；
- 引用与事实核验；
- 前端交互；
- 成本、安全和隐私控制。

如果把这些都放进一个简历项目，常见结果是功能名很多，但每条都只有薄薄的样例实现，老师一追问“怎么证明”“失败怎么办”“真实并发在哪里”，项目就失去可信度。

### 2.3 缩小后的主动命题

2026-06-06 的 scope 设计将主线缩为：

> 展示一个 LangGraph Agent 工程从结构化规划、固定角色、真实并发、工具授权、证据身份、claim 支持门禁到审计产物的完整闭环。

对应规格：

- `docs/superpowers/specs/2026-06-06-evidence-research-agent-resume-scope-design.md`
- Git 提交 `71b6704`：`docs: narrow project to evidence research agent`

缩小不是放弃原始愿景，而是选择其中技术密度最高、最容易被严格验证的一段。

### 2.4 为什么这个切片适合升学面试

它同时能讨论：

- AI Agent 的定义与边界；
- LLM 概率输出和确定性程序之间的分工；
- 多智能体是否真实并发；
- Tool Calling 的权限与 Schema；
- RAG/证据约束和幻觉控制；
- Pydantic 结构化输出；
- LangGraph 动态图执行；
- provenance、auditability 和 fail-closed；
- 测试 LLM 系统的方法；
- 系统局限如何转化为研究问题。

它不是靠 UI 或大规模数据撑场面，而是靠可解释的技术边界和测试证据。

---

## 3. 项目目标、非目标与成功标准

### 3.1 当前目标

当前项目回答的是：

> 如何让 LLM 在一个有界研究任务中动态组织多个临时研究实例，同时不让模型直接控制证据身份、工具权限、引文内容和最终报告释放？

### 3.2 当前非目标

以下能力不是当前主动路径的完成项：

- 实时全网监控；
- 自动每日推送；
- 全量社媒舆情采集；
- 完整事件聚类与时间线；
- 情感分类模型；
- 事实真实性判定；
- 来源可信度评分；
- 群体代表性推断；
- 长期对话产品；
- 生产级容错与分布式扩缩容。

### 3.3 成功标准

项目在当前范围内成立，需要满足：

1. 一个命令可以运行完整研究流程；
2. Forum Host 只能从固定角色中规划；
3. 至少两个 worker LLM 调用可以真实重叠；
4. 角色越权工具调用在执行前被拒绝；
5. Evidence ID 必须来自真实工具输出；
6. 报告 claim 必须引用已存储 evidence；
7. 引文支持失败时不生成报告；
8. 运行过程可以通过 trace 和 sidecar 检查；
9. 单元与集成测试不依赖真实网络；
10. 真实服务运行能验证适配器路径，但不把一次 smoke test 夸大为生产可靠性。

---

## 4. 基础知识

## 4.1 LLM 是什么

Large Language Model 是根据上下文对后续 token 概率分布进行建模的神经网络。现代通用 LLM 通常基于 Transformer，通过 self-attention 建模序列中 token 之间的关系。

对本项目最重要的性质不是“它很聪明”，而是：

- 输出具有概率性；
- 它擅长从自然语言中规划、归纳和生成结构；
- 它可能产生格式错误、事实错误、虚构引用和越界推断；
- 即使 `temperature=0`，不同服务实现、模型版本和底层算子仍可能导致差异；
- 它不能仅凭 Prompt 获得真正的文件、网络或数据库访问权，必须通过工具接口。

本项目的 OpenAI-compatible adapter 在
`opinion_agent/llm/openai_compatible.py` 中将 `temperature` 设为 `0`，目的是降低随机性，不是宣称数学上的完全确定性。

### 4.1.1 Token、上下文与推理

LLM 不直接处理“词义”，而是先将文本切分为 token，再根据上下文预测输出 token。一次 API 请求通常经历：

```text
text -> tokenizer -> token IDs -> model forward/inference
-> token distribution -> decoding -> output tokens -> text
```

上下文窗口限制了单次请求可以容纳的 Prompt、工具结果和历史状态。项目对 tool call 数、evidence 数和 content 长度做上限控制，也是在控制上下文膨胀。

### 4.1.2 Transformer 与 Self-Attention

Transformer 的核心之一是 self-attention。简化表达为：

```text
Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V
```

- Query 表示当前位置想查找什么信息；
- Key 表示每个位置可被匹配的特征；
- Value 表示匹配后聚合的内容；
- 多头注意力让模型从不同子空间学习关系。

本项目没有修改或训练 Transformer，而是把预训练模型作为概率决策组件使用。老师若问“你的创新是否在模型结构”，应回答不是，重点在 Agent runtime、证据契约和验证边界。

### 4.1.3 Hallucination

Hallucination 通常指模型生成了看似合理但缺乏依据、与来源不符或现实错误的内容。可以进一步区分：

- **内在矛盾**：生成内容与给定来源冲突；
- **外部无依据**：来源未提供该信息；
- **引用幻觉**：来源、URL、评论或引文不存在；
- **范围幻觉**：把局部 sample 扩大为整体结论；
- **工具幻觉**：模型声称执行了实际未执行的工具。

本项目主要控制引用幻觉、工具幻觉和一部分范围扩大，不解决所有现实事实错误。

### 4.1.4 Prompt Engineering、RAG 与 Fine-tuning

- **Prompt Engineering**：通过指令和上下文约束模型行为；
- **RAG**：先检索外部信息，再让模型基于检索结果生成；
- **Fine-tuning**：用训练数据更新模型参数，使其适应任务或格式。

本项目使用 Prompt、Tool-based retrieval 和 structured output，但没有微调模型。原因是当前主要失败来自权限、身份和证据链，单纯微调不能替代确定性校验。

### 4.1.5 Embedding 与 NLI

Embedding 将文本映射为向量，可用于相似度检索，但“相似”不等于“支持”。两个语义相似句子可能在否定、时间或主体上冲突。

Natural Language Inference 通常判断 premise 对 hypothesis 是 entailment、contradiction 还是 neutral。它比 embedding similarity 更接近 claim-support 问题，因此是未来 semantic evaluator 的候选方向，但仍需要领域数据、校准和 abstention 机制。

## 4.2 Agent 是什么

一个实用的软件定义是：

> Agent 是一个以目标和状态为条件，由模型参与决策，并可通过工具改变外部状态或获得新观察的执行系统。

典型循环是：

```text
goal/state -> decide -> act with tool -> observe -> update state -> continue/stop
```

本项目是“有界 Agent”，因为：

- 角色集合固定；
- 研究轮数固定为一轮；
- 并发实例数有上限；
- 每个 worker 的工具调用最多 3 个；
- 工具集合由代码安装并按角色取交集；
- Citation Agent 最多两次选择尝试；
- 最终只允许支持门禁通过后输出。

它不是无限自主运行的 AutoGPT 类系统。

## 4.3 Agent 与普通工作流有什么区别

普通工作流的路径通常由程序员完全写死，例如：

```text
search -> summarize -> report
```

Agent 工作流允许模型在受控位置作决策。本项目中：

- Forum Host 决定任务如何分解以及选哪些可执行研究角色；
- worker 决定本任务需要哪些被允许的工具调用；
- Citation Agent 决定选哪个候选 source span；
- Report Writer 决定已验证 claims 的顺序。

但以下事项不交给模型：

- 角色注册；
- 权限判定；
- 工具真实执行；
- Evidence ID 生成；
- 候选文本物化；
- 支持门禁；
- Markdown 渲染；
- 文件写入和 trace 脱敏。

因此它介于刚性 pipeline 与无限自治 Agent 之间。

## 4.4 Tool Calling 是什么

Tool Calling 是模型输出结构化“调用意图”，程序再决定是否执行某个函数或外部 API。

必须区分：

1. **模型声称调用了工具；**
2. **模型输出了合法 Tool Call；**
3. **程序验证并实际执行了 Tool Call；**
4. **工具返回结果并被规范化为证据。**

只有第 4 步之后，信息才进入本项目的证据层。

`opinion_agent/agents/models.py` 中的 `ToolCallRecord` 定义：

```python
tool_id: ToolId
arguments: dict
```

`ToolId` 是固定 `Literal`，不能由运行时随意创造。随后
`opinion_agent/tools/registry.py` 还会再次检查：

- 工具是否注册；
- 当前角色是否在 whitelist 中；
- 参数是否通过工具对应的 Pydantic input model；
- handler 是否执行成功。

## 4.5 Structured Output 是什么

Structured Output 要求模型输出符合某个数据 Schema，而不是返回难以解析的自由文本。

例如 Forum Host 必须返回 `ResearchPlan`，worker 第一阶段必须返回
`SubagentActionPlan`。

优点：

- 程序可以明确检查字段和类型；
- 可以拒绝未知角色、重复 task ID、超限工具调用；
- 控制流不依赖脆弱的正则解析；
- 测试可以直接构造和断言对象。

局限：

- Schema 合法不代表语义正确；
- 一个格式正确的查询仍可能无关；
- 一个合法 candidate ID 选择仍可能不是最佳来源；
- Provider 的“structured output”能力本身也可能失败。

## 4.6 Pydantic、Schema 与运行时验证

Pydantic 将 Python 类型声明转为运行时验证规则。

本项目使用它实现：

- `Literal` 限制角色、工具、claim type 和 verdict；
- `Field(min_length=...)` 拒绝空值；
- `max_length=3` 限制 worker 工具调用数；
- `ConfigDict(frozen=True)` 降低对象被意外修改的风险；
- `extra="forbid"` 拒绝模型偷偷添加报告正文等额外字段；
- `model_validator` 检查 task/claim ID 唯一性；
- `field_validator` 检查 scope 文本和 ID 格式。

Schema 是边界，不是完整安全方案。项目仍需要权限检查、ID 交叉验证和确定性支持验证。

## 4.7 Multi-Agent 是什么

Multi-Agent 系统包含多个相对独立的决策或执行实体。这里的“多”不是在一个 Prompt 里写：

```text
你现在分别扮演搜索员、评论员和编辑……
```

本项目中的 worker：

- 有独立 task；
- 有独立角色 Prompt、Skills 和 Tool Set；
- 发起独立 `model.ainvoke`；
- 可以同时处于等待真实服务响应的状态；
- 返回独立的 `SubagentResult`；
- 最终由 reducer 合并。

因此它是运行时层面的多实例，而不是文本层面的角色扮演。

## 4.8 固定角色与临时实例

“固定角色”描述能力模板，“临时实例”描述某一轮中的执行对象。

例如：

- `query_agent` 是固定定义；
- `task_01_features` 和 `task_02_safety` 可以是两个临时
  `query_agent` 实例；
- 两者共享角色约束，但 task、Prompt payload、调用时间和结果不同。

项目禁止 Forum Host 创建 `rumor_expert` 之类的新角色，因为运行时创造角色会绕过预先审查的 Skills、Tool Set 和 Schema。

## 4.9 LangGraph `StateGraph`

LangGraph 用带状态的有向图组织 Agent 工作流。

项目在 `opinion_agent/graph/research.py` 中：

```python
builder = StateGraph(ResearchState)
```

并添加三个 runtime node：

- `plan_research`
- `run_subagent`
- `prepare_claims`

需要特别说明：Citation Agent、support gate 和 Report Writer 不在这个
`StateGraph` 内，而是在 `ResearchService` 中按确定性顺序编排。

## 4.10 State、Node 与 Edge

- **State**：节点共享和更新的数据；
- **Node**：接收状态并返回状态增量的执行单元；
- **Edge**：定义节点之间的转移；
- **Conditional Edge**：根据当前状态动态决定下一步。

`ResearchState` 位于 `opinion_agent/graph/state.py`，包含：

- `topic`
- `plan`
- `subagent_results`
- `evidence_records`
- `trace_events`
- `errors`
- `stage`

## 4.11 `Send`、fan-out 与 fan-in

`Send` 允许一个节点根据运行时 plan 动态创建多个到同一 worker node 的执行分支。

`fan_out_research_tasks` 对每个 `ResearchTask` 返回一个：

```python
Send("run_subagent", {"topic": topic, "task": task})
```

这叫 **fan-out**。

多个 worker 完成后，它们的结果合并回共享状态并进入
`prepare_claims`，这叫 **fan-in**。

## 4.12 Reducer

并发分支不能随意覆盖同一个状态字段，需要定义合并规则。

项目用：

```python
Annotated[list[SubagentResult], operator.add]
```

为以下字段配置列表拼接 reducer：

- `subagent_results`
- `evidence_records`
- `trace_events`
- `errors`

这样每个分支返回一个局部列表，fan-in 时由 reducer 合并，而不是最后完成的分支覆盖前一个分支。

## 4.13 异步并发、并行与 Python GIL

本项目证明的是 **异步 I/O 并发**：

- 多个 LLM 网络请求可以同时处于进行中；
- 一个请求等待网络时，事件循环可以推进其他请求；
- 这不等于多个 Python CPU 密集任务在多个 CPU 核上并行计算。

Python GIL 主要限制同一进程中 Python bytecode 的 CPU 并行，而本项目主要等待 HTTP/模型 I/O，因此 `asyncio` 并发有实际意义。

面试中更严谨的说法是：

> 我实现并证明了真实 worker LLM 请求的并发重叠，而不是宣称实现了 CPU parallel computing。

## 4.14 Provenance

Provenance 是数据从哪里来、经过什么过程进入系统的可追溯信息。

本项目的 evidence metadata 保存：

- `task_id`
- `role_id`
- `query`
- `provider_request_id`
- provider metadata
- 是否截断及原始字符数

它回答“这条 evidence 是哪个任务通过哪个查询和 provider 得到的”，但不回答“provider 内容一定真实”。

## 4.15 Evidence、Claim、Citation、Support

- **Evidence**：存储的来源记录或来源片段；
- **Claim**：报告想表达的一个可独立验证断言；
- **Citation**：claim 指向哪些 evidence ID；
- **Support**：被引用 evidence 是否在 claim 声明的类型和范围内支持它。

这四者不能混用。

例如：

```text
Evidence: 某网页中确实出现“路线调整范围有限”
Claim: “路线调整范围有限”
Citation: ev-abc
Support: exact span 存在，因此 direct_quote 得到 supported
```

但不能推出：

```text
这个路线调整客观上一定有限
所有市民都认为调整有限
媒体整体持支持态度
```

## 4.16 Auditability

Auditability 指事后可以检查：

- 模型规划了什么任务；
- 哪些角色实例启动；
- 调用了什么工具；
- 产生了哪些 evidence ID；
- claim 选择和验证结果是什么；
- 是否写出报告。

本项目的 `trace.json`、`evidence.jsonl` 和
`report_verification.json` 提供这种可检查性。

它不是完整 replayability。没有保存模型原始 Prompt、完整响应、随机状态、provider 版本和 LangGraph checkpoint，因此不能保证逐步重放得到相同结果。

---

## 5. 系统架构与边界

## 5.1 两层编排

系统不是“所有东西都在 LangGraph 里”。

### LangGraph 研究层

文件：`opinion_agent/graph/research.py`

职责：

- Forum Host 规划；
- 验证计划的数量与可执行能力；
- `Send` fan-out；
- worker 两阶段执行；
- reducer fan-in；
- 汇总 research-stage 错误与 trace。

### 确定性服务层

文件：`opinion_agent/research/service.py`

职责：

- 创建独占 run directory；
- 调用研究图；
- 持久化 evidence；
- 构造 quote candidates；
- 调用 Citation Agent；
- 物化 `ClaimInput`；
- 运行 support gate；
- 调用 Report Writer 生成 claim 顺序；
- 确定性写报告、sidecar 和 trace。

这种分层使 LangGraph 专注动态研究，而关键释放门禁仍由普通 Python 控制流清晰掌握。

## 5.2 信任边界

| 数据/动作 | 是否信任 | 处理方式 |
|---|---|---|
| 用户 topic | 不完全信任 | 去除空白、报告渲染时转义 Markdown/HTML |
| LLM plan | 不信任 | Pydantic 校验、覆盖 canonical topic、检查角色能力和实例上限 |
| LLM tool call | 不信任 | 固定 Tool ID、角色权限、安装状态、参数 Schema |
| Tool/provider output | 不信任 | 类型解析、数量和长度限制、metadata 隔离 |
| LLM evidence IDs | 不信任 | 必须是本 worker 执行工具后生成的 available IDs |
| Citation Agent selection | 不信任 | candidate ID 必须存在，否则重试后拒绝 |
| Support evaluator output | 不直接信任 | 再校验 claim identity、scope、span 和 verdict invariants |
| Report Writer output | 不信任 | 只能返回 verified claim ID 排序，集合必须完全一致 |
| 文件输出 | 受程序控制 | 转义、临时文件替换、独占 run directory |

---

## 6. 完整控制流与数据流

## 6.1 总表

| 阶段 | 控制者 | 输入 Schema | 输出 Schema/数据 | 主要拒绝条件 |
|---|---|---|---|---|
| 创建运行 | `ResearchService` | topic/output dir | run ID、空 evidence 文件 | run ID 目录已存在 |
| 规划 | Forum Host LLM | topic、可执行角色 | `ResearchPlan` | 空 topic、未知/不可执行角色、超实例数 |
| fan-out | LangGraph | `ResearchPlan` | 多个 `Send` | plan 缺失 |
| 工具计划 | worker LLM | `ResearchTask`、permitted tools | `SubagentActionPlan` | Schema 错误、工具数 > 3、非法 Tool ID |
| 工具执行 | Python `ToolRegistry` | Tool Call | `ToolResult` | 未注册、越权、参数错误、handler 错误 |
| 证据规范化 | Python | `ToolResult` | Evidence Records | 非成功结果、非支持的数据类型 |
| 受限总结 | worker LLM | tool results、available IDs | `SubagentResult` | 引用未知 evidence ID |
| fan-in | LangGraph reducer | 各 worker 增量 | 合并 ResearchState | worker 错误被记录 |
| 证据落盘 | `EvidenceStore` | records | `evidence.jsonl` | 缺失 ID；重复 ID 不重复写 |
| 候选构造 | Python | stored evidence | quote candidates | 无可用文本 |
| 引文选择 | Citation Agent LLM | candidates | `CitationSelectionBundle` | 未知 candidate；最多修复一次 |
| claim 物化 | Python | selection + candidate | `ClaimBundle` | candidate 不存在、claim ID 不合法 |
| support gate | Python + evaluator | claim + cited evidence | `ClaimVerificationResult` | 任意非 supported 或契约不一致 |
| 报告排序 | Report Writer LLM | verified claims | `ReportOutline` | 漏 claim、加 claim、重复 ID、额外 prose |
| 报告落盘 | Python renderer | ordered verified claims | report + sidecar | 再验证失败 |
| trace 落盘 | Python sanitizer | events/errors | `trace.json` | 敏感字段被删除或脱敏 |

## 6.2 运行入口

CLI 位于 `opinion_agent/cli.py`：

```powershell
python -m opinion_agent research `
  --topic "A bounded social event" `
  --adapter fake `
  --output-dir output\research
```

`--adapter fake` 使用离线确定性模型和搜索 fixture。默认 `real` 会读取真实配置并构建 OpenAI-compatible model 与 Anspire search。

## 6.3 Run directory

`ResearchService.run` 先生成：

```text
run-<12 hex chars>
```

再调用：

```python
run_dir.mkdir(parents=True, exist_ok=False)
```

`exist_ok=False` 是关键。若目录已存在，立即抛出 `FileExistsError`，不会向旧 evidence 文件追加数据。

## 6.4 规划

`plan_research`：

1. 清理并检查 topic 非空；
2. 读取 `forum_host` 的 system prompt 和 Skills；
3. 计算当前真正可执行的研究角色；
4. 要求模型返回 `ResearchPlan`；
5. 如果模型重写 topic，代码将它覆盖回用户原始 canonical topic；
6. 检查全局 `max_parallel_subagents`；
7. 检查每个角色的 `max_instances`；
8. 检查所选角色是否有已安装工具适配器。

## 6.5 动态 fan-out

计划中每个 task 产生一个 `Send("run_subagent", ...)`。因此：

- task 数量不是编译图时写死；
- 同一种角色可以开多个实例；
- 不需要为每个实例预定义节点；
- 角色仍必须属于固定 `ResearchRoleId`。

## 6.6 worker 执行

每个 worker 的有效工具集合是：

```text
role.tool_ids ∩ installed_tool_ids
```

不是 Prompt 自己声明的工具，也不是全局所有工具。

worker 第一阶段返回 `SubagentActionPlan`。程序逐个执行其中的 tool call，规范化证据，再把真实 tool result 和 `available_evidence_ids` 送回同一角色做第二阶段总结。

同一 worker 内多个工具调用当前是顺序执行；不同 worker 分支可以并发。

## 6.7 worker 失败

`run_subagent` 捕获异常并返回：

- 一个带 `errors` 的 `SubagentResult`；
- 全局 `errors` 增量；
- `subagent_failed` trace event。

LangGraph 仍可保留其他成功 worker 的结果。但 `ResearchService` 发现全局错误后会将整次运行标记为 `rejected`，不会继续生成报告。

这体现：

- 研究图层允许观察部分成功；
- 最终发布层不接受部分失败的研究结果。

## 6.8 fan-in

所有 worker 的：

- result；
- evidence records；
- trace events；
- errors

通过 reducer 合并。`prepare_claims` 当前不生成 claim，只将阶段设为
`research_complete` 并记录 `research_fan_in_completed`。

这个命名反映了历史演进；真正的 claim 准备在图外的 service 中完成。

## 6.9 evidence 持久化

service 在 fan-in 后将 evidence records 逐条追加到本运行独有的
`evidence.jsonl`。

如果：

- 任意 worker 错误存在，运行 rejected；
- 最终没有任何 evidence，运行 rejected；
- 不会在无 evidence 情况下调用 Citation Agent。

## 6.10 quote candidates

`_build_quote_candidates` 对 evidence content 生成有界候选：

- 优先提取句子状片段；
- 单个候选约束在 20 到 500 字符；
- 每条 evidence 最多取 3 个候选；
- 若无法提取句子但 content 非空，回退到前 500 字符；
- candidate ID 由 `evidence_id:index` 构成。

候选文本由代码直接来自已存 evidence，不由 LLM 生成。

## 6.11 Citation Agent

Citation Agent 收到 topic、candidate 列表、attempt 和上一次 gate error。

它只能返回：

```json
{
  "selections": [
    {
      "claim_id": "claim-1",
      "candidate_id": "ev-...:0"
    }
  ]
}
```

`CitationSelectionBundle` 当前 `min_length=1, max_length=1`，所以主动研究路径最终只选择一个 claim。

如果 candidate ID 不存在：

- 第一次失败记录 `claim_repair_requested`；
- 第二次仍失败则整个 run rejected。

## 6.12 Claim 物化

`_materialize_claims` 根据 candidate 查表，程序生成：

- `claim_type="direct_quote"`
- `text=candidate["text"]`
- `evidence_ids=(candidate["evidence_id"],)`
- `scope.platform=source_name or "unknown"`
- `scope.sample="single collected source excerpt"`
- 若有 `published_at`，生成同起止时间的 `time_window`

因此模型无法：

- 改一个标点；
- 拼接两段引文；
- 将 paraphrase 冒充 direct quote；
- 给 claim 换一个未引用 evidence ID。

## 6.13 Support gate

`verify_claim_support`：

1. 验证 `ClaimInput`；
2. 按 claim 中的 ID 顺序读取 evidence；
3. 缺失或重复 ID 时在 evaluator 前拒绝；
4. 调 evaluator；
5. 重新验证 assessment Schema；
6. 检查 assessment 的 claim ID、type、scope；
7. 检查 assessment span 只引用 claim 已引用的 evidence；
8. 检查 quote 真在对应 content 中；
9. 检查 verdict invariants；
10. 只有 `supported` 才令 result valid。

## 6.14 Report Writer

Report Writer 不写标题和正文，只返回：

```python
ReportOutline(
    ordered_claim_ids=(...)
)
```

代码要求其 ID 集合与全部 verified claims 完全相同。它不能：

- 漏掉 claim；
- 添加新 claim；
- 重复 claim；
- 添加 prose 字段。

## 6.15 最终落盘

`write_report_artifacts` 会再次验证全部 claim，然后写：

- `report.md`
- `report_verification.json`

`ResearchService._finish` 最后写：

- `trace.json`

完整目录：

```text
output/research/run-<id>/
  evidence.jsonl
  report.md
  report_verification.json
  trace.json
```

---

## 7. 七种固定角色

角色注册表位于 `opinion_agent/agents/registry.py`，并用
`MappingProxyType` 暴露为不可变映射。

| Role ID | 职责 | Skills | Tool Set | 实例上限 | 当前状态 |
|---|---|---|---|---:|---|
| `forum_host` | 规划有界研究、选择研究角色 | `research_planning`, `gap_analysis` | 无 | 1 | **[已实现并测试]** |
| `query_agent` | 搜索可归因 web 材料 | `web_research`, `source_triage` | `web_search`, `store_evidence` | 4 | **[已实现并测试]**；真实 `web_search` 已验证 |
| `database_researcher` | 检索既有 evidence/report | `evidence_retrieval`, `prior_report_review` | `search_evidence`, `read_evidence` | 2 | **[仅定义契约]** |
| `multimedia_researcher` | 提取有界媒体观察 | `multimedia_inspection`, `source_triage` | `inspect_media`, `store_evidence` | 2 | **[仅定义契约]** |
| `citation_agent` | 选择确定性 source-span candidate | `claim_atomization`, `citation_audit` | `read_evidence`, `verify_citations`, `verify_claim_support` | 2 | **[已实现并测试]** |
| `report_writer` | 排列已验证 claims | `evidence_synthesis`, `report_writing` | `read_evidence`, `write_report` | 1 | **[已实现并测试]** |
| `tikhub_researcher` | 收集有界社媒记录 | `social_media_research`, `source_triage` | `tikhub_search`, `store_evidence` | 3 | **[仅定义契约]** |

### 7.1 为什么不允许临时创造新角色

如果 Forum Host 能临时发明角色，就可能同时发明：

- 未审查的 system prompt；
- 未知的工具权限；
- 不兼容的输入输出格式；
- 无上限的实例；
- 无测试的行为。

固定角色使能力可以预先审查和测试。临时性保留在“实例和任务”层，而不是“权限模板”层。

### 7.2 为什么仍然叫动态多智能体

固定角色并不意味着固定工作队列。动态性体现在：

- Forum Host 根据 topic 选择是否使用某角色；
- 同一角色可创建多个实例；
- task 数量和内容由本轮 plan 生成；
- LangGraph 根据 plan 动态产生 `Send`。

---

## 8. Skills、Tool Sets 与最小权限

## 8.1 Skill 的含义

Skill 是角色的行为说明模块，定义“如何做”，例如：

- 优先主来源；
- 保留 title、URL 和时间；
- 不把 provider summary 当原始 evidence；
- 把报告视为线索而非一手证据；
- 区分媒体中的直接观察与解释；
- 不把有限社媒 sample 泛化为全部公众。

Skill 注册表位于 `opinion_agent/agents/skills.py`。

## 8.2 Tool Set 的含义

Tool Set 是角色允许调用的工具白名单，定义“能做什么”。

Skill 不是权限控制。即使 Prompt 写着“不要越权”，真正的权限仍由
`ToolRegistry.invoke` 检查。

## 8.3 最小权限原则

Least privilege 指每个主体只获得完成任务所需的最小权限。

本项目有三层限制：

1. `ToolId` 是固定 Literal；
2. role definition 声明 whitelist；
3. runtime 只暴露 whitelist 与实际 installed tools 的交集。

例如 `database_researcher` 不能调用 `web_search`，即便模型输出了这个合法的全局 Tool ID。

## 8.4 为什么角色定义有工具，但 adapter 未必存在

角色契约描述系统未来可支持的能力，Tool Registry 描述本次运行真正安装的能力。

只有两者交集才可执行。当前 real factory 只注册 `web_search`，因此真实路径只有 `query_agent` 是可执行研究 worker。

如果 planner 选择 `tikhub_researcher`，图会在 worker 启动前抛出
`ResearchPlanCapabilityError`，而不是假装执行。

还要区分“角色 Tool Set 契约”和“当前调用路径”：

- 研究 worker 的工具通过 `ToolRegistry` 执行并做运行时权限检查；
- 当前 `query_agent` 实际安装的是 `web_search`，`store_evidence` 由 graph/service 的确定性代码完成，并不是模型主动调用的工具；
- `citation_agent` 和 `report_writer` 虽定义了工具白名单，但当前 service 直接调用确定性 evidence lookup、verifier 和 report renderer，没有让这两个 LLM 角色通过 `ToolRegistry` 执行这些工具；
- 因此不能声称“七个角色的所有 Tool IDs 都已有可调用 adapter”。

---

## 9. 结构化契约

## 9.1 ResearchTask

字段：

- `task_id`
- `role_id`
- `objective`
- `rationale`

`role_id` 只能是四种研究 worker：

- `query_agent`
- `database_researcher`
- `multimedia_researcher`
- `tikhub_researcher`

Citation Agent 和 Report Writer 不允许被 Forum Host 当普通研究 worker 调度。

## 9.2 ResearchPlan

包含 canonical `topic` 和至少一个 task。

额外不变量：

- task ID 唯一；
- task 总数不超过全局上限；
- 每种 role 不超过 role 上限；
- role 必须有安装的工具能力。

## 9.3 SubagentActionPlan

包含：

- canonical task ID；
- canonical role ID；
- 1 到 3 个 `ToolCallRecord`。

即便模型返回了改写后的 task/role identity，runtime 也会用当前分支的真实 task 覆盖，防止模型改变授权主体。

## 9.4 SubagentResult

包含：

- task/role identity；
- summary；
- evidence IDs；
- 实际 tool calls；
- errors。

模型返回的 evidence IDs 必须是本 worker 当前工具执行产生的
`available_evidence_ids` 子集。

## 9.5 CitationSelectionBundle

当前只允许一个 selection。字段只有：

- `claim_id`
- `candidate_id`

`extra="forbid"`，模型不能附加 quote text。

## 9.6 ReportOutline

只有：

- `ordered_claim_ids`

ID 必须唯一，额外字段被拒绝。最终还要与 verified claim set 完全相等。

---

## 10. 两阶段 worker 设计

### 10.1 第一阶段：Action Planning

模型看到：

- topic；
- task ID；
- objective；
- rationale；
- permitted tools。

它返回结构化 tool calls。

### 10.2 程序阶段：Tool Execution

程序：

- 检查 tool 是否在 permitted set；
- 通过 `ToolRegistry` 再做权限检查；
- 验证参数；
- 执行 handler；
- 将结果转为 `ToolResult`；
- 规范化 evidence。

### 10.3 第二阶段：Evidence-constrained Synthesis

模型看到：

- 原 task；
- 真实 tool results；
- 程序生成的 available evidence IDs。

它只能从这些 ID 中选择引用。

### 10.4 为什么不让模型一次性完成

单 Prompt 方式可能让模型同时输出：

- “我搜索到了……”；
- 虚构 URL；
- 虚构 evidence ID；
- 无法区分的推理与来源文本。

两阶段设计把“决定查什么”和“根据查到的内容总结”分开，并在中间加入真实工具和程序控制的证据身份。

### 10.5 仍然存在的局限

- 第二阶段 summary 没有直接进入最终报告，因此它主要是可检查的 worker 产物；
- Tool Result 中失败项不会规范化为 evidence；
- 当前没有自动重试单个 tool call；
- 同一 worker 内多个 tool calls 顺序执行；
- 没有 query quality evaluator 或搜索覆盖率指标。

---

## 11. 证据规范化与稳定 ID

代码：`opinion_agent/evidence/normalizer.py`

## 11.1 有界化

每个 tool call：

- 最多保存 3 个搜索结果；
- 每条 content 最多保存 4000 字符。

这限制：

- 单个模型计划导致的内存和文件膨胀；
- provider 返回异常大文本；
- 后续 candidate 和 Prompt 体积。

## 11.2 稳定 identity

stored identity 包括：

- `source_type`
- `source_name`
- `url`
- `title`
- `published_at`
- 截断后的 `content`

此外，hash identity 加入完整原文的 SHA-256：

```text
content_sha256 = SHA256(original_content)
```

然后对 canonical JSON 进行 SHA-256，取前 24 个十六进制字符：

```text
evidence_id = "ev-" + digest[:24]
```

## 11.3 为什么必须 hash 完整原文

早期风险是只对存储的 4000 字符前缀做 hash。

如果两个来源：

- 前 4000 字符相同；
- 后续内容不同；

它们会得到同一个 ID，导致去重错误和 provenance 混淆。

修复后，ID 同时反映完整原文 hash，即使存储内容被截断，也能区分不同尾部。

## 11.4 Provider metadata 为什么嵌套

provider 自带 metadata 被放在：

```text
metadata.provider_metadata
```

而 trusted runtime provenance：

- `task_id`
- `role_id`
- `query`
- `provider_request_id`
- truncation fields

由程序单独写入。

这样 provider 不能通过返回同名字段覆盖可信 provenance。

## 11.5 “稳定”不等于“绝对唯一”

稳定表示相同规范化输入重复生成相同 ID，不表示理论上没有 hash collision。

当前使用 96 bit 截断 digest，工程上碰撞概率很低，但若进入高规模生产系统，可以：

- 保存完整 digest；
- 建唯一索引；
- 冲突时比较完整 identity；
- 使用内容寻址存储。

---

## 12. EvidenceStore 与 JSONL

代码：`opinion_agent/evidence/store.py`

### 12.1 为什么用 JSONL

JSON Lines 每行一条 JSON record，适合当前项目：

- 简单；
- 可人工检查；
- append-only；
- 便于 GitHub 示例；
- 无需引入数据库服务；
- 测试中可临时创建。

### 12.2 行为

- evidence 必须有非空 ID；
- 已存在 ID 不重复写；
- `read_all` 读取全部；
- `get_many` 保留请求顺序；
- 请求重复 ID 会拒绝；
- 缺失 ID 会明确列出；
- 返回 deep copy，避免 evaluator 修改持久化记录。

### 12.3 局限

- 每次 `exists` 会读取整个文件，规模大时效率低；
- 没有数据库索引；
- 没有跨进程文件锁；
- 没有 schema migration；
- 没有 evidence 更新和版本管理；
- 当前适合本地、单 run、作品集规模。

---

## 13. Citation Agent 为什么只选 candidate ID

### 13.1 遇到的真实问题

最初让 LLM 复制 source quote，即使 Prompt 要求 exact quote，真实模型仍可能：

- 改标点；
- 去掉前后词；
- 合并句子；
- 规范化空格；
- 做轻微 paraphrase。

这会导致 `ExactQuoteEvaluator` 拒绝，或迫使系统使用模糊匹配，削弱可审计性。

### 13.2 最终方案

程序先从 evidence 生成候选：

```text
candidate_id -> evidence_id + exact text
```

Citation Agent 只做一个更适合 LLM 的任务：

> 哪个候选与当前 bounded topic 最相关？

随后程序查表物化 claim。

### 13.3 技术意义

这是“缩小模型写权限”的例子：

- 保留 LLM 的语义选择能力；
- 收回字符级复制权限；
- 引文文本和 evidence ID 成为不可分离的程序映射；
- exact quote gate 不再依赖模型复制稳定性。

### 13.4 为什么不是让 Citation Agent 返回 quote 再校验

返回 quote 再校验也能 fail closed，但会造成大量本可避免的失败和重试。

ID 选择让“合法输出空间”从任意字符串缩小为有限候选集合，可靠性更高。

---

## 14. Claim Contract

代码：`opinion_agent/citations/models.py`

## 14.1 四种 claim type

| 类型 | 含义 | 当前 evaluator 状态 |
|---|---|---|
| `direct_quote` | claim text 是来源中的完整原文 span | **[已实现并测试]** |
| `factual_statement` | 来源直接表达的事实或忠实转述 | **[仅定义契约]**，当前为 `indeterminate` |
| `opinion_summary` | 对声明 sample 中意见的有界汇总 | **[仅定义契约]**，当前为 `indeterminate` |
| `analytic_inference` | 从 evidence 推出的解释或结论 | **[仅定义契约]**，当前为 `indeterminate` |

## 14.2 为什么先声明类型

不同 claim 需要不同验证方法。

- direct quote 可以做 exact substring；
- factual statement 需要语义蕴含或事实核验；
- opinion summary 需要 sample aggregation；
- analytic inference 需要论证结构和不确定性处理。

如果不声明类型，开发者容易把 exact string evaluator 偷偷扩展成“语义验证器”。

## 14.3 Scope

可选 scope：

- `platform`
- `time_window.start/end`
- `sample`

scope 的作用是防止范围悄悄扩大。

例如：

```text
sample = single collected source excerpt
```

只表示一条收集片段，不代表所有来源或全部公众。

当前实现验证和保留 scope，但不会自动判断 scope 是否合理，也不会从一条来源推断总体。

## 14.4 ID 约束

claim/evidence IDs 只允许：

```text
[A-Za-z0-9][A-Za-z0-9._:-]{0,127}
```

这样可以：

- 拒绝空白和过长 ID；
- 防止 ID 中嵌入换行；
- 降低 Markdown 结构注入；
- 保持 trace 和 sidecar 易读。

---

## 15. ExactQuoteEvaluator 与 fail-closed

## 15.1 ExactQuoteEvaluator 做什么

代码：`opinion_agent/citations/evaluators.py`

若且唯若：

- `claim_type == "direct_quote"`；
- 完整 claim text 是任一 cited evidence content 的精确 span；

才返回 `supported`。

匹配只规范化换行：

- `\r\n` -> `\n`
- `\r` -> `\n`

它不会：

- 折叠空白；
- 改标点；
- 分词；
- 翻译；
- 做 fuzzy match；
- 判断语义等价。

## 15.2 为什么其他类型返回 indeterminate

返回 `unsupported` 可能暗示 evaluator 判断了语义但证据不足。实际上 exact quote evaluator 根本没有能力判断 paraphrase 或 inference。

因此更诚实的 verdict 是：

```text
indeterminate
```

## 15.3 Verdict

四种 verdict：

- `supported`
- `unsupported`
- `contradicted`
- `indeterminate`

当前 exact evaluator 实际产生 `supported`、`unsupported` 或
`indeterminate`。`contradicted` 契约为未来 evaluator 预留。

## 15.4 Fail-closed

Fail-closed 表示：

> 只有明确证明满足条件才放行；系统无法判断时默认拒绝。

以下全部拒绝：

- claim 格式错误；
- scope 格式错误；
- evidence ID 缺失或重复；
- evidence 不存在；
- evaluator 抛异常；
- assessment 格式错误；
- assessment identity/scope 不匹配；
- 引用未被 claim 声明的 evidence；
- supporting quote 不在 evidence 中；
- supported 但没有 supporting span；
- supported 同时存在 contradicting span；
- unsupported/contradicted/indeterminate。

## 15.5 Support 不等于 truth

本项目的 supported 应理解为：

> 在 claim 声明的类型与 scope 下，持久化 evidence 中存在通过当前 evaluator 和确定性校验的支持 span。

它不等于：

- 来源说法是真实世界事实；
- 来源可信；
- 多个来源相互独立；
- 样本有代表性；
- 大多数公众持该意见；
- 事件因果关系成立。

---

## 16. 报告、sidecar、trace 与文件原子性

## 16.1 报告为什么由程序渲染

早期风险是让模型写标题和正文。即使 claims 已验证，模型仍可能在连接句或标题中加入：

- 未验证事实；
- 范围扩大；
- 情绪性措辞；
- 新的解释。

最终设计让 Report Writer 只排 claim IDs，Markdown 由
`opinion_agent/reports/generator.py` 确定性渲染。

## 16.2 报告内容

报告包含：

- 由 topic 确定的标题；
- 当前日期；
- claim ID；
- `Claim:` 前缀和 claim text；
- claim type；
- scope；
- evidence ID；
- exact excerpt；
- source name/type/title/URL；
- gate 声明。

## 16.3 为什么加 `Claim:` 前缀

即使转义了常见 Markdown 字符，单独一行：

```text
---
```

仍可能被 Markdown 解释为 thematic break。

固定前缀：

```text
Claim: ---
```

使不可信 claim text 不能独占块级结构位置。

## 16.4 Markdown 与 HTML 注入控制

`_safe_inline`：

- 将换行折叠为空格；
- 使用 HTML escape；
- 转义反斜杠、反引号、星号、括号、`#`、`|` 等 Markdown 字符。

这保护的是生成文档结构，不是浏览器层完整 XSS 防护体系。

## 16.5 Verification sidecar

`report_verification.json` 保存：

- schema version；
- topic；
- 原 claim 输入；
- claim type 和 scope；
- assessment；
- evaluator ID/version；
- supporting spans 和 verdict。

它比只看 Markdown 更适合机器检查。

## 16.6 Trace

`trace.json` 保存：

- run ID、topic、status；
- UTC event time；
- role/task identity；
- planning task；
- model/tool duration；
- tool arguments；
- evidence IDs；
- verification verdict；
- report completion；
- errors。

它不保存：

- API keys；
- Authorization headers；
- system/user Prompt；
- hidden reasoning；
- provider 完整 payload。

## 16.7 Trace 脱敏

`opinion_agent/tracing/run_trace.py`：

- 递归删除 forbidden keys；
- 对所有字符串替换已配置 secrets；
- 对错误字符串也脱敏；
- 对 top-level run ID/topic/status 也脱敏；
- 使用正则遮盖未提前注册的 Bearer token；
- tuple/list/dict 嵌套结构都递归处理。

## 16.8 原子写入的准确表述

run directory 使用原子式独占创建，避免同一 run ID 混写。

报告、sidecar 和 trace 分别：

1. 写入 `.tmp`；
2. 使用 `Path.replace` 替换目标文件。

这降低“目标文件只写了一半”的风险。

但必须准确说明：

- report 和 sidecar 是两个独立 replace；
- 它们不是数据库事务；
- 极端情况下第一个 replace 成功而第二个失败，可能留下单个 artifact；
- 当前没有 crash recovery 和 manifest commit protocol。

---

## 17. 并发真实性与证明

## 17.1 不能怎样证明

只比较：

```text
串行预计 6 秒，实际 3 秒
```

不是可靠单元测试，因为机器负载、缓存和服务延迟会变化。

## 17.2 Barrier test

`tests/fakes.py` 中的 `BarrierStructuredModel`：

1. 每个 worker action-plan 调用记录自己的 task ID；
2. 调用在 `asyncio.Event` 上等待；
3. 只有至少两个 task 都启动后，event 才释放；
4. 若第二个调用没有在超时前进入，测试失败。

`tests/test_research_graph.py` 的
`test_graph_runs_real_parallel_subagent_calls_and_reduces_results` 断言：

- `worker_overlap_observed is True`；
- 两个 task 都启动；
- 两个结果和两条 evidence 都被 reducer 保留；
- fan-in event 只出现一次。

这是确定性地证明调度重叠，而不是推测。

## 17.3 真实服务 overlap

真实冒烟记录中三个 action-plan LLM 调用：

| Task | 开始 UTC | 结束 UTC | 时长 |
|---|---|---|---:|
| `task_01_features` | 07:11:27.957779 | 07:11:30.556804 | 2599.025 ms |
| `task_02_commercial` | 07:11:27.958558 | 07:11:31.486303 | 3527.745 ms |
| `task_03_safety` | 07:11:27.959037 | 07:11:32.412995 | 4453.958 ms |

三个区间重叠，说明真实 provider 路径也没有退化成串行。

## 17.4 两类证据的关系

- Barrier test 证明程序调度性质；
- real smoke 证明真实 adapter 集成中确实观察到重叠；
- real smoke 不是稳定性能 benchmark；
- 一次成功 smoke 不证明长期可用性、吞吐量或 provider SLA。

---

## 18. 技术路线迭代

## 18.1 阶段一：确定性个人舆情 MVP

规格日期：2026-06-05。

先实现：

- sample collector；
- JSONL evidence store；
- citation existence；
- calm briefing；
- bounded conversation policy；
- LangGraph-compatible descriptor。

目的：先让数据和边界可测试，再引入真实 LLM。

当前状态：这些代码仍保留为 **[历史原型]**。

## 18.2 阶段二：缩小主动范围

提交 `71b6704`：

```text
docs: narrow project to evidence research agent
```

将简历主线从完整个人舆情产品缩为 evidence-research slice。

## 18.3 阶段三：配置、角色、工具与模型边界

按提交顺序：

- `82b858d`：generic runtime settings；
- `7419a8f`：fixed role registry；
- `d4576ee`：role tool permissions；
- `8cf553e`：structured model adapter。

这一步先建立“谁能做什么、输入输出是什么”的边界。

## 18.4 阶段四：真实动态并发

- `584b25b`：LangGraph dynamic parallel subagents；
- 引入 `StateGraph`、`Send`、reducers 和 barrier test。

## 18.5 阶段五：证据必须来自执行过的工具

- `794709f`：derive evidence from executed tools；
- 引入两阶段 worker 和 evidence normalizer；
- 拒绝模型自己生成 evidence IDs。

## 18.6 阶段六：从 citation existence 升级为 support gate

- `16e9f16`：enforce claim support gate；
- 将“ID 存在”与“文本支持”分开；
- 加入 claim type、scope、assessment、sidecar 和 fail-closed report。

## 18.7 阶段七：端到端编排和可审计产物

- `d2f86db`：orchestrate auditable research runs；
- `262bd8c`：add runnable research workflow；
- 加入 `ResearchService`、trace、fake/real factory、CLI 和 sample report。

## 18.8 阶段八：真实服务暴露问题后的硬化

- `8aa4f0d`：harden real provider research workflow。

这一阶段不是单纯加功能，而是根据真实运行和代码审查收缩信任面：

- Citation Agent 从写 quote 改为只选 candidate ID；
- Report Writer 从写标题/正文改为只排 claim IDs；
- trace 深层脱敏；
- run ID 独占目录；
- tool call 上限；
- full-content hash；
- provider metadata 隔离；
- Markdown 注入防护；
- adapter capability 检查；
- unknown evidence/candidate 拒绝；
- 文档纠正为一轮、可检查但不可完整 replay。

---

## 19. 开发中遇到的具体困难与修复

## 19.1 LLM 引文复制不稳定

**现象**

真实模型可能对原文做微小改写，导致 exact quote 失败。

**根因**

语言模型优化的是合理 token 序列，不是字符级复制一致性。

**修复**

程序生成 candidate，Citation Agent 只返回 candidate ID，程序物化 quote。

**抽象经验**

当合法输出来自有限集合时，让模型“选 ID”通常比“重写值”可靠。

## 19.2 模型写标题/正文扩大信任面

**风险**

已验证 claims 之间的模型连接句仍可增加未验证内容。

**修复**

`ReportOutline` 只允许 ordered claim IDs；标题来自 topic；正文由程序模板渲染；`extra="forbid"`。

**抽象经验**

不要只验证输入事实，还要限制生成器能新增什么语义。

## 19.3 Trace 嵌套或字符串化泄密

**风险**

只删除顶层 `api_key` 不够。secret 可能出现在：

- nested dict；
- list/tuple；
- error message；
- `"provider rejected key xxx"`；
- top-level topic/run ID；
- 未注册 Bearer token。

**修复**

递归 key 过滤、全字符串替换、错误脱敏、top-level 脱敏和 Bearer 正则。

**抽象经验**

日志安全是数据流问题，不是“删几个字段”问题。

## 19.4 重复 run ID 混合旧产物

**风险**

若复用目录，新的 evidence 可能追加到旧 run，破坏审计身份。

**修复**

`mkdir(exist_ok=False)`，目录已存在即失败；并发测试证明两个相同 ID 的 run 中只能一个获得目录。

**抽象经验**

审计系统首先要保证一次运行的 artifact namespace 独占。

## 19.5 Tool call 无界

**风险**

模型可能生成大量调用，导致成本、延迟和数据体积不可控。

**修复**

`SubagentActionPlan.tool_calls` 限制 1 到 3；同时限制 worker 数、每角色实例数、每调用 evidence 数和 content 长度。

**尚未解决**

没有 token/人民币成本预算，没有全局请求速率限制。

## 19.6 截断内容导致 Evidence ID collision

**风险**

两个文档前 4000 字符相同、尾部不同，若只 hash 存储前缀，会误认为同一 evidence。

**修复**

hash identity 加入完整原文 SHA-256，存储仍保持 4000 字符上限。

## 19.7 Provider metadata 覆盖 provenance

**风险**

外部 provider 返回 `task_id`、`role_id` 等同名字段，若直接 merge 可能伪造来源链。

**修复**

provider metadata 嵌套到 `provider_metadata`；runtime provenance 单独写入。

## 19.8 Markdown 结构注入

**风险**

topic、claim、source title 等来源文本可能包含标题、表格、HTML、换行或 thematic break。

**修复**

折叠换行、HTML escape、Markdown 特殊字符 escape、ID regex、`Claim:` 固定前缀。

## 19.9 Planner 选择没有 adapter 的角色

**风险**

注册表中定义了 database/multimedia/TikHub，不代表本次运行可执行。

**修复**

图构建时计算 role tool whitelist 与 installed tools 的交集；规划后执行 capability validation。

## 19.10 模型发明 Evidence ID

**风险**

worker summary 输出形似合法但不存在的 `ev-...`。

**修复**

程序收集本 worker 的 `available_evidence_ids`，检查模型结果必须是其子集。

## 19.11 Citation Agent 返回未知 candidate

**风险**

模型可能拼错或创造 candidate ID。

**修复**

程序查 deterministic candidate map；未知 ID 触发一次 repair；再次失败则 rejected。

## 19.12 模型重写 topic/task/role identity

**风险**

模型输出 Schema 合法但将 task ID 或 role ID 改成另一身份，可能混淆权限和审计。

**修复**

topic 由用户输入覆盖；worker result/action plan 中 task/role 由当前 runtime 分支覆盖。

---

## 20. 系统性与抽象挑战

## 20.1 概率组件与确定性保证如何组合

LLM 适合：

- task decomposition；
- query planning；
- 有限候选语义选择；
- 证据受限总结。

确定性代码适合：

- 权限；
- identity；
- Schema；
- 数据持久化；
- exact matching；
- release gate；
- 渲染和日志脱敏。

项目的核心不是“消灭 LLM 不确定性”，而是让不确定性只存在于允许的决策区域。

## 20.2 多智能体的收益是否大于复杂度

多智能体增加：

- 更多模型调用；
- 更复杂状态合并；
- 更难调试；
- 更高成本；
- 更多失败模式。

本项目用它的理由是研究任务可自然拆成独立 evidence gap，并且需要展示动态 fan-out。若任务只有一个简单查询，Forum Host 应生成更少 task，而不是为了“多 Agent”强行开角色。

## 20.3 “可审计”与“可信”不是同义词

可审计表示可以检查过程。可信还需要：

- 来源质量；
- 数据完整性；
- evaluator validity；
- 威胁模型；
- 统计代表性；
- 重复实验。

当前项目只建立可审计基础，不宣称整体结论已达到科学事实核验标准。

## 20.4 Fail-closed 与可用性的冲突

严格门禁会拒绝更多结果。例如真实模型只改一个标点，旧方案也会失败。

解决方式不应是放宽到模糊匹配，而是重新设计接口，让模型选 deterministic ID。

这体现可靠系统常见原则：

> 优先改变生成空间，而不是不断为不稳定输出增加宽松补丁。

## 20.5 Scope 与代表性

“一条微博中出现某观点”和“公众普遍持某观点”之间缺少：

- 抽样框；
- 样本量；
- 时间窗口；
- 去重；
- 账号真实性；
- 平台偏差；
- 统计估计。

因此 scope 是必要契约，但仅保存 scope 还不能完成代表性分析。

---

## 21. 详细边界情况

| 边界情况 | 当前行为 | 原因/剩余风险 |
|---|---|---|
| topic 为空或纯空白 | 规划前拒绝 | 防止无目标运行 |
| Planner 改写 topic | 用用户 topic 覆盖 | 保持 canonical user intent |
| 重复 task ID | Pydantic 拒绝 | reducer 和 trace 需要唯一身份 |
| task 超全局上限 | `ResearchPlanLimitError` | 控制并发规模 |
| 单角色实例超限 | `ResearchPlanLimitError` | 防止模型集中滥开实例 |
| 角色无安装 adapter | `ResearchPlanCapabilityError` | 契约不等于实现 |
| 全部工具未安装 | graph build 失败 | 至少需一个可执行研究角色 |
| 模型输出未知 Tool ID | Schema 或 registry 拒绝 | 不能动态发明工具 |
| 合法 Tool ID 但角色越权 | 执行前 `ToolPermissionError` | least privilege |
| 工具参数类型错误 | `ToolResult(ok=False)` | 错误类型化，不调用 handler |
| Tool handler 异常 | `execution_error` | 不让异常伪装成证据 |
| Tool 失败但 worker 仍总结 | 无 evidence 可引用；可能产生空结果 | 当前未对单 tool 做自动重试 |
| Provider 返回非 JSON/object/list | search adapter 拒绝 | 防止非预期 payload |
| 搜索结果过多 | 每调用最多 3 条 evidence | 有界化 |
| content 过长 | 存前 4000 字符，hash 完整原文 | 可能丢失后半段可引用内容 |
| Provider metadata 伪造 role ID | 保存在嵌套 provider metadata | trusted provenance 不被覆盖 |
| 模型发明 evidence ID | worker 失败并记录错误 | 只能引用本次工具生成 ID |
| 一个 worker 失败、一个成功 | 图保留两者，service 整体 rejected | 不发布部分研究 |
| 全部 worker 无 evidence | Citation Agent 不运行，rejected | 无证据不生成 claim |
| evidence content 为空 | 不形成可用 quote candidate | 无文本无法 exact quote |
| candidate ID 拼错 | 一次 repair，仍错则 rejected | 有界恢复 |
| claim ID 含 Markdown/换行 | Schema 拒绝 | 保护 identity 和输出结构 |
| evidence ID 重复引用 | Claim Schema/get_many 拒绝 | 避免歧义 |
| evidence ID 不存在 | evaluator 前拒绝 | 避免 evaluator 在错误 bundle 上工作 |
| claim 是 paraphrase | exact evaluator 为 unsupported 或 indeterminate | 当前只支持 direct quote |
| claim type 是 inference | `indeterminate`，报告不生成 | 不假装语义验证 |
| evaluator 抛异常 | 转为 indeterminate，fail closed | 不因 evaluator 故障放行 |
| evaluator 引用未 cited evidence | verifier 拒绝 | evaluator 也不能扩大 evidence bundle |
| supporting span 不存在 | verifier 拒绝 | 防 evaluator 虚构 quote |
| supported 无 supporting span | verifier 拒绝 | verdict 必须有可检查依据 |
| supported 同时有 contradiction | verifier 拒绝 | 契约不一致 |
| Report Writer 漏/加 claim | service 拒绝 | 只能排列完整 verified set |
| Report Writer 输出正文 | `extra="forbid"` | 收缩模型写权限 |
| topic/source 含 Markdown | inline sanitize | 防止改变文档结构 |
| claim text 为 `---` | 渲染成 `Claim: ---` | 防 thematic break |
| run ID 已存在 | 创建目录失败，不触碰旧文件 | 防 artifact 混合 |
| 两个并发 run 同 ID | 只有一个成功占目录 | 文件系统原子创建 |
| 进程在两个 artifact replace 间崩溃 | 可能只存在一个 artifact | 当前无跨文件事务 |
| Trace error 中包含 key | 字符串替换/正则脱敏 | 未知 secret 格式仍可能是残余风险 |
| Provider 改模型版本 | 当前 trace 不完整记录 provider model revision | 无法精确 replay |
| evidence 相同但 provider metadata 不同 | ID 主要由 source/content identity 决定 | metadata 变化未必生成新 ID |
| 96-bit 截断 hash 碰撞 | 未显式冲突解决 | 作品集规模风险很低，生产需加强 |

---

## 22. 测试地图

当前测试应通过：

```powershell
python -m pytest tests -q -p no:cacheprovider
```

本文档编写时的完整回归结果为 `99 passed`。这个数字描述当前提交附近的测试基线；后续新增测试后应以最新 CI 或本地结果为准。

### 22.1 角色与 Schema

`tests/test_agent_registry.py`

证明：

- 只有批准的七种角色；
- 每个角色绑定 Skills、Tools、contracts 和 limits；
- role/skill registry 不可变；
- 未知角色拒绝；
- Forum Host 不能作为 worker；
- task IDs 唯一；
- runtime 不能发明 Tool ID；
- action plan 工具调用数有上限；
- ReportOutline 不能包含模型正文。

### 22.2 Tool Registry 与搜索适配器

`tests/test_tool_registry.py`

证明：

- permission 在 handler 前检查；
- 参数验证后才执行；
- 未知 tool 拒绝；
- handler failure 变成 typed result；
- Anspire adapter 保留来源 metadata；
- malformed provider output 拒绝。

### 22.3 LLM adapter

`tests/test_llm_adapter.py`

证明：

- structured output 被 Pydantic 验证；
- malformed output 拒绝；
- provider failure 被包装；
- 错误不泄漏 API key；
- real adapter 使用 temperature 0。

### 22.4 LangGraph 与并发

`tests/test_research_graph.py`

证明：

- 每个 task 产生一个 `Send`；
- worker action-plan calls 真实重叠；
- reducer 保留所有结果和 evidence；
- 单 worker 失败不覆盖成功 worker；
- 全局和角色实例上限；
- 无 adapter 角色拒绝；
- 模型发明 evidence ID 拒绝；
- topic/task/role canonical identity 由 runtime 掌握。

### 22.5 Evidence

`tests/test_evidence_normalizer.py`

证明：

- stable evidence IDs；
- failed tool 不生成 evidence；
- 结果数和 content 长度有界；
- full original content 参与 identity；
- provider metadata 不能覆盖 provenance。

`tests/test_evidence_store.py`

证明：

- JSONL append/read；
- ID 必填；
- duplicate 不重复写；
- `get_many` 保序并返回独立对象；
- duplicate/missing requested IDs 拒绝。

### 22.6 Citation 与 support

`tests/test_citation_verifier.py`

证明 citation existence 层的：

- existing ID 通过；
- unknown/missing/non-list IDs 拒绝。

`tests/test_claim_support.py`

证明：

- exact direct quote 支持；
- semantic claim indeterminate；
- invented supporting span 拒绝；
- missing evidence 在 evaluator 前拒绝；
- scope 验证和保存；
- identifier Markdown injection 拒绝。

### 22.7 Report

`tests/test_report.py`

证明：

- supported claim 写 Markdown 与 sidecar；
- unsupported 不写任何报告 artifact；
- duplicate claim ID 拒绝；
- title 确定性且非模型作者；
- Markdown/HTML 结构注入处理；
- `---` claim 不成为 thematic break。

### 22.8 ResearchService

`tests/test_research_service.py`

证明：

- 完整 artifact 链路；
- 关键 trace events 和 duration；
- Citation/Report structured calls 确实发生；
- unsupported/invalid candidate 不生成报告；
- 无 evidence 时 Citation Agent 不运行；
- gate rejection 后最多一次 repair；
- Citation Agent 不能写 quote/evidence ID；
- reused run ID 不触碰旧 artifact；
- 并发相同 run ID 只能一个成功。

### 22.9 Trace

`tests/test_run_trace.py`

证明：

- forbidden keys 递归删除；
- event value/error 中 secret 脱敏；
- 未注册 Bearer token 脱敏；
- top-level strings 脱敏。

### 22.10 Settings 与 CLI

`tests/test_settings.py`

证明：

- generic LLM/search settings；
- required values 缺失时 fail closed；
- TikHub 可选但必须成对配置；
- limits 有类型和边界；
- `.env.example` 不含 secret value。

`tests/test_cli.py`

证明：

- 历史 brief/report/conversation 命令仍运行；
- fake research 完整链路；
- real settings 缺失时明确失败。

### 22.11 测试没有证明什么

测试通过不证明：

- 搜索召回率高；
- LLM plan 是最优的；
- 真实网络长期稳定；
- 来源真实；
- 舆情 sample 有代表性；
- 系统能抵御所有 Prompt injection；
- 性能达到生产要求。

---

## 23. Fake 与 Real Adapter

## 23.1 Fake adapter

文件：

- `opinion_agent/research/fake.py`
- `opinion_agent/research/factory.py`

特性：

- 无 API key；
- 无网络；
- 固定生成两个 query tasks；
- 每个 task 产生一个 deterministic search result；
- Citation Agent 选第一个 candidate；
- Report Writer 按输入顺序输出 IDs。

用途：

- 本地演示；
- CI；
- 端到端回归；
- 区分 orchestration bug 与 provider bug。

它不模拟真实 LLM 的全部错误分布。

## 23.2 Real adapter

配置：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`
- `SEARCH_PROVIDER`
- `SEARCH_API_KEY`
- `SEARCH_BASE_URL`
- `MAX_PARALLEL_SUBAGENTS`
- `LLM_REQUEST_TIMEOUT`
- `SEARCH_TIMEOUT`

可选但当前未接入 Tool Registry：

- `TIKHUB_API_KEY`
- `TIKHUB_BASE_URL`

真实 model 使用 OpenAI-compatible `ChatOpenAI.with_structured_output`。

真实 search 当前只支持 `SEARCH_PROVIDER=anspire`。

## 23.3 一个共享模型 Profile

所有角色当前共享一套 model endpoint 和 model name。

角色差异来自：

- system prompt；
- Skills；
- Tool Set；
- input/output Schema；
- instance/task。

这是为了把重点放在 orchestration，不把项目变成多 provider 路由系统。

## 23.4 配置安全

- secrets 使用 `SecretStr`；
- `.env` 被忽略；
- `.env.example` 只有空 placeholder；
- model adapter 错误会替换 API key；
- trace factory 将已配置 secret values 传给 sanitizer。

面试时不要展示真实 key、Authorization header 或本地凭据路径。

---

## 24. 不能声称的能力

以下表述不准确：

### 24.1 “这是一个生产级舆情监控平台”

不准确。当前是一轮、有界、作品集规模的研究 Agent，没有调度、持续采集、分布式处理和生产 SLA。

### 24.2 “已经接入数据库、多媒体和 TikHub”

不准确。它们有固定角色、Skills 和 Tool IDs，但真实 adapter 尚未实现。

### 24.3 “系统能验证事实真实性”

不准确。ExactQuoteEvaluator 验证的是文本 span 支持，不验证现实世界真值。

### 24.4 “系统能判断舆论整体趋势”

不准确。当前没有代表性抽样、群体统计、跨平台加权和趋势模型。

### 24.5 “支持所有 claim 的语义验证”

不准确。只有 `direct_quote` 可通过当前 evaluator。其他三种 type 返回
`indeterminate`。

### 24.6 “七种 Agent 都在每次运行”

不准确。角色固定可选；当前 real adapter 实际可执行的研究角色是
`query_agent`。Citation Agent 和 Report Writer 在 service 后段运行。

### 24.7 “整个系统都是 LangGraph”

不准确。LangGraph 负责研究阶段；citation、verification、report 和 artifact 由 service 层编排。

### 24.8 “实现了多轮自主反思”

不准确。当前一轮 research；Citation Agent 选择失败后最多 repair 一次，不是完整的多轮 gap analysis。

### 24.9 “Trace 可以完整重放”

不准确。Trace 可检查，但未保存完整 Prompt/response、checkpoint、模型 revision 和随机状态。

### 24.10 “temperature 0 所以完全确定”

不准确。它降低采样随机性，provider、模型版本和系统实现仍可能变化。

---

## 25. 工程未来方向与研究问题

## 25.1 工程扩展

1. 实现 `database_researcher` 的 read-only adapter 和索引；
2. 实现 TikHub bounded collection，保留平台、作者、时间和互动 metadata；
3. 实现多媒体 evidence schema 与观察/解释分离；
4. 引入多轮 gap-driven research，并设置明确终止条件；
5. 添加 token、请求数和人民币预算；
6. 工具重试、熔断、rate limit 和 provider fallback；
7. EvidenceStore 升级到有索引的数据库；
8. 引入 LangGraph checkpoint 和 resumable run；
9. artifact manifest/transaction，提升 crash consistency；
10. 建立离线 benchmark 和回归数据集；
11. Prompt injection 与恶意来源测试；
12. source deduplication、canonical URL 和内容版本；
13. 前端只作为检查和交互层，不改变证据门禁。

## 25.2 语义支持研究

可以比较：

- LLM-as-a-judge；
- Natural Language Inference；
- claim decomposition + NLI；
- retrieval-conditioned verifier；
- 多 evaluator ensemble；
- calibration 与 selective prediction。

关键指标：

- supported precision/recall；
- unsupported rejection rate；
- hallucinated span acceptance rate；
- abstention quality；
- scope expansion error；
- evaluator consistency；
- 成本和延迟。

## 25.3 来源可信度研究

支持关系成立后，还需要单独研究：

- 来源类型与权威性；
- 原始来源/转载链；
- 多源独立性；
- 交叉印证；
- 时间一致性；
- 来源编辑历史；
- 恶意内容和 Prompt injection。

## 25.4 舆情代表性研究

需要明确：

- target population；
- sampling frame；
- platform bias；
- demographic bias；
- bot/coordination；
- engagement weighting；
- duplicate/repost；
- uncertainty interval；
- temporal drift。

## 25.5 多 Agent 是否真的更好

可设计消融实验：

- 单 Agent vs 多 Agent；
- 固定任务 vs Forum Host 规划；
- 串行 vs 并发；
- 无 role-specific Skills vs 有 Skills；
- unrestricted tools vs least privilege；
- 模型写 quote vs candidate selection；
- 模型写报告 vs deterministic renderer。

测量：

- evidence coverage；
- invalid citation rate；
- task redundancy；
- latency；
- token cost；
- failure rate；
- report support precision。

## 25.6 精神卫生目标如何研究

原始愿景可转化为 HCI/AI 研究问题：

- 低刺激 brief 是否降低无目的滚动时长；
- 主动 deep dive 是否提升信息保持；
- 多视角报告是否降低情绪极化；
- 模型批判用户假设是否提高判断质量或造成反感；
- 如何测量“信息充分”与“心理负担”之间的平衡；
- 如何避免系统自己成为新的 engagement optimizer。

---

## 26. 分层面试题与参考回答

## 26.1 基础层

### Q1：什么是 LLM Agent？

**参考回答**

LLM Agent 是以目标和状态为条件，由 LLM 参与决策，并能通过工具获得观察或改变外部状态的系统。与单次文本生成不同，Agent 有决策、行动、观察和终止边界。本项目中 LLM 负责研究规划、工具计划和有限候选选择，程序负责权限、执行、证据身份、验证和输出。

**可能追问：你的系统自主到什么程度？**

它是有界自治：可以动态拆任务和开临时 worker，但角色、工具、实例数、调用数、研究轮数和报告门禁都由代码限制。

### Q2：工作流和 Agent 的区别是什么？

**参考回答**

工作流路径由开发者预先确定，Agent 在某些节点由模型决定下一步。本项目保留固定的大框架，但 Forum Host 动态决定 task，worker 动态决定被允许的 tool call，因此是 Agentic workflow，而不是无限自治系统。

### Q3：什么是 Tool Calling？

**参考回答**

模型输出结构化调用意图，程序验证后执行真实函数。模型写出“调用搜索”不等于搜索发生了。本项目只有 `ToolRegistry` 执行成功并经过 normalizer 后的数据才成为 evidence。

### Q4：Structured Output 有什么用？

**参考回答**

它把自由文本转换为可验证的对象，例如 `ResearchPlan`。Pydantic 可以检查角色 Literal、字段类型、ID 唯一性和工具数上限。但 Schema 只能保证结构，不能保证语义正确，因此仍要做权限和交叉验证。

### Q5：为什么用 Pydantic？

**参考回答**

它把模型边界变成运行时契约，支持类型、范围、Literal、frozen model、extra forbid 和自定义 validator。相比手写字典判断，错误更系统，也方便测试和 structured output adapter 复用。

### Q6：temperature 设为 0 是否完全可复现？

**参考回答**

不能。它通常让选择更集中，但 provider 实现、模型版本、浮点计算和服务更新仍可能变化。项目的可复现部分主要来自 fake adapter 和确定性验证，不依赖真实 LLM 字符级稳定。

### Q7：这个项目算 RAG 吗？

**参考回答**

广义上是 retrieval-augmented、evidence-grounded generation，因为模型通过工具获得外部证据再总结。但它不是典型向量数据库 RAG：当前 retrieval 是 web search，重点是 provenance、ID 和 support gate，而不是 embedding similarity。

### Q8：为什么没有向量数据库？

**参考回答**

当前范围是一轮 web research，JSONL 足以展示证据身份和验证闭环。加向量数据库会增加部署和调参复杂度，却不直接加强当前最重要的 claim-support story。数据库检索保留为后续 adapter。

## 26.2 架构层

### Q9：为什么选择 LangGraph？

**参考回答**

项目需要运行时 task 数量可变的 fan-out、异步 worker、显式 state 和 reducer fan-in。LangGraph 的 `StateGraph` 和 `Send` 对这类动态 Agent workflow 表达清晰，同时比手写大量 task orchestration 更容易把状态合并规则显式化。

**追问：为什么 citation/report 不也放入图？**

当前把动态研究放在图中，把安全关键的验证和 artifact release 放在普通 service 控制流中，便于审查和 fail-closed。未来需要 checkpoint 或多轮图时可以再扩大 graph，但当前没有为了“全图化”牺牲清晰度。

### Q10：`Send` 是什么？

**参考回答**

`Send` 是 LangGraph 的动态分支原语。Forum Host 生成几个 task，函数就返回几个指向 `run_subagent` 的 `Send`，每个携带自己的 task input。它允许运行时决定 fan-out 数量。

### Q11：Reducer 为什么必要？

**参考回答**

并发分支都要写 `subagent_results`、`evidence_records` 等字段。没有 reducer，更新可能冲突或覆盖。项目用 `Annotated[list, operator.add]` 明确将分支列表拼接。

### Q12：如何证明是真并发，不是多角色 Prompt？

**参考回答**

每个 task 发起独立 `model.ainvoke`。确定性测试用 `asyncio.Event` barrier，只有两个 worker 都进入 action-plan 调用才释放；若串行就超时失败。真实 smoke 中三个模型调用的开始和结束时间区间也重叠。

### Q13：异步并发与并行有什么区别？

**参考回答**

异步并发是多个任务在等待 I/O 时交错推进，不一定同时在多个 CPU 核运算。这个项目主要证明网络请求 overlap，不宣称 CPU parallelism。

### Q14：为什么角色固定但实例临时？

**参考回答**

固定角色便于预审权限、Skills 和 Schema；临时实例让 Forum Host 根据 topic 动态分配任务。这样兼顾动态性和治理，不允许模型在运行时创造未审查权限模板。

### Q15：为什么用一个共享模型而不是每个角色不同模型？

**参考回答**

当前重点是 Agent orchestration。角色通过 Prompt、Skills、Tool Set 和 Schema 区分。共享 profile 减少 provider routing 和配置噪音。未来可基于成本或能力为角色分配模型，但不是当前证明点。

## 26.3 证据与幻觉层

### Q16：项目如何减少幻觉？

**参考回答**

不是靠一句“不要幻觉”的 Prompt，而是逐步缩小模型权限：

1. 工具由程序执行；
2. evidence ID 由 tool output 生成；
3. worker 只能引用本次 available IDs；
4. quote candidates 由代码从 evidence 生成；
5. Citation Agent 只选 candidate ID；
6. direct quote 做 exact span verification；
7. Report Writer 不能新增正文；
8. 非 supported 全部 fail closed。

### Q17：citation existence 和 support 有什么区别？

**参考回答**

existence 只说明 ID 对应的 evidence 存在；support 说明该 evidence 是否支持具体 claim。真实来源可以与 claim 无关，所以报告使用 `verify_claim_support`，不能只检查 ID。

### Q18：support 和 truth 有什么区别？

**参考回答**

support 是文本或语义关系，truth 是现实世界属性。来源中确实出现一句话，只能证明“来源说过”，不能证明这句话为真。来源可信度和交叉核验是独立层。

### Q19：为什么只支持 direct quote？

**参考回答**

因为 exact substring 是确定、便宜、可复核的基线。若把它延伸到 paraphrase 或 inference，会制造虚假的语义保证。项目先用 `claim_type` 明确能力边界，其他类型返回 indeterminate，等待正式 semantic evaluator。

### Q20：为什么不用关键词重叠验证语义？

**参考回答**

词汇重叠不等于蕴含，否定、主体变化、时间变化都可能有高重叠但语义相反。关键词规则容易给出错误 supported，比明确 abstain 更危险。

### Q21：Citation Agent 还算 Agent 吗？它只选一个 ID。

**参考回答**

它仍用 LLM 根据 topic 和候选语义作选择，但动作空间被严格限制。Agent 能力不等于必须生成长文本。安全关键场景中，把 Agent 的 action space 设计成有限集合是合理的。

### Q22：为什么 support evaluator 的输出还要再验证？

**参考回答**

Evaluator 也是可失败组件。即便它返回 structured assessment，也可能引用未提供的 evidence、虚构 quote、claim ID 不匹配或给出自相矛盾 verdict。程序必须校验 assessment invariants。

## 26.4 工程与安全层

### Q23：Least privilege 如何实现？

**参考回答**

全局 Tool ID 是 Literal，角色有 whitelist，runtime 只暴露 whitelist 与 installed tools 的交集，`ToolRegistry` 在 handler 前再次检查角色权限，参数还要通过 input Schema。

### Q24：Prompt injection 怎么处理？

**参考回答**

当前主要通过结构隔离和权限边界降低影响：来源内容不能改变 Tool Registry，模型不能生成 evidence ID，Citation Agent 只能选 candidate，Report Writer 不能写 prose，输出会转义。但项目还没有完整恶意网页 benchmark，也不能宣称抵御所有 Prompt injection。

### Q25：为什么 trace 不保存 Prompt？

**参考回答**

避免泄漏 secret、内部指令和潜在敏感内容，也避免把 hidden reasoning 当审计要求。代价是 trace 只能 inspect，不能完整 replay。未来可以保存经过审查的 prompt template version 和 input hash，而不是原始敏感文本。

### Q26：如何避免日志泄密？

**参考回答**

递归删除敏感 key，对所有字符串、错误和 top-level 字段替换已知 secret，并额外识别 Bearer token。测试覆盖 nested dict、stringified error 和 top-level secret。

### Q27：为什么 run ID collision 很严重？

**参考回答**

如果两个 run 共用目录，evidence、report 和 trace 会混合，审计关系失效。项目使用 `mkdir(exist_ok=False)` 原子竞争目录，并测试并发相同 ID 只有一个成功。

### Q28：文件写入是完全事务性的吗？

**参考回答**

不是。每个目标文件通过 temp + replace 避免半文件，但 report 和 sidecar 之间没有跨文件事务。未来可使用 manifest、staging directory 后整体 rename，或数据库事务。

### Q29：为什么要限制 tool calls 和 evidence size？

**参考回答**

控制延迟、成本、Prompt 体积和恶意/异常 provider 输出。当前限制每 worker 计划最多 3 个工具调用，每调用最多 3 条 evidence，每条最多 4000 字符。

### Q30：Evidence ID 为什么不用随机 UUID？

**参考回答**

内容派生 ID 使相同 evidence 可重复识别和去重，便于审计。随机 UUID 只保证一次生成的唯一性，不表达内容 identity。当前实现仍需承认 96-bit 截断 hash 的理论碰撞可能。

## 26.5 质疑层

### Q31：这是不是“套壳 API”？

**参考回答**

项目确实调用外部 LLM 和搜索服务，但技术重点不在训练模型，而在 Agent runtime：动态 fan-out、角色权限、结构化契约、证据身份、支持门禁、并发证明和审计产物。需要诚实说明它是 LLM 应用工程项目，不是基础模型训练项目。

### Q32：为什么不直接一个强模型完成全部任务？

**参考回答**

单模型可以完成简单样例，但很难隔离权限和审计不同任务。多实例允许独立 evidence gaps 并发处理，并给每类任务不同 Tool Set。代价是成本和复杂度，所以 Forum Host 应保持任务最少化。

### Q33：一个最终 claim 能叫舆情分析吗？

**参考回答**

不能把当前输出夸大为完整舆情分析。当前主动 slice 验证的是 research-and-evidence pipeline。`CitationSelectionBundle` 目前只选一个 direct quote，属于技术闭环最小实现。扩展到多 claim、多来源意见汇总和代表性分析是后续工作。

### Q34：真实 smoke 只有一次，说明什么？

**参考回答**

说明真实 provider、真实搜索、structured output、并发和 artifact 链路至少成功集成过一次。它不说明可靠率、性能分布或生产稳定性，这些需要重复实验和监控。

### Q35：为什么不做模型训练或微调？

**参考回答**

当前研究问题是如何通过 runtime contracts 控制模型行为，主要瓶颈不是领域语言能力，而是权限、身份和验证。若未来积累 claim-support 数据集，可研究 NLI 或 evaluator 微调，但不应为展示“训练”而加入无数据依据的微调。

### Q36：项目最大的不足是什么？

**参考回答**

当前 evidence support 很窄：只验证直接引文，不验证事实真实性、来源可信度和样本代表性；真实 adapter 也只有 web search。优点是边界明确且 fail closed，下一步可以围绕 semantic verifier 和 source/sample quality 做研究。

## 26.6 研究层

### Q37：如何评价 semantic evaluator？

**参考回答**

建立人工标注 claim-evidence 数据集，覆盖 supported、unsupported、contradicted、indeterminate，特别加入否定、时间错位、主体错位、范围扩大和 adversarial quote。测 precision、recall、abstention quality、calibration、成本和延迟。

### Q38：如何评价多 Agent 是否有效？

**参考回答**

做单 Agent/多 Agent 消融，在相同 topic 和预算下比较 evidence coverage、重复率、invalid citation rate、latency、token cost 和最终 supported claim 数。只看输出更长不能证明更好。

### Q39：如何研究舆情代表性？

**参考回答**

先定义目标总体和抽样框，再记录平台、时间窗、去重和账号属性；分析平台偏差、机器人、转发和 engagement bias；报告带不确定性而不是把 sample 频率直接叫公众比例。

### Q40：如何把“精神卫生”变成可研究指标？

**参考回答**

可以做用户研究，比较社媒 feed 与 bounded brief 在阅读时长、情绪唤醒、信息记忆、主观负担、判断校准和继续滚动冲动上的差异，同时评估模型批判性是否帮助独立判断。

---

## 27. 30 秒、2 分钟与 5 分钟口述框架

## 27.1 30 秒

> 我做的是一个基于 LangGraph 的有界舆情证据研究智能体。Forum Host 会把主题拆成任务，用 `Send` 并发启动固定角色的临时 LLM 实例。模型只能提议工具调用，权限、真实执行和 evidence ID 都由程序控制。为了防止引用幻觉，Citation Agent 不复制引文，只选择程序从证据生成的 candidate ID；当前只对 direct quote 做 exact-span 验证，任何不确定情况都 fail closed。最后输出报告、验证 sidecar 和脱敏 trace。这个项目强调的是 Agent 工程边界和可审计性，不是生产级全网监控。

## 27.2 2 分钟

建议顺序：

1. 动机；
2. 架构；
3. 最关键防幻觉设计；
4. 并发证明；
5. 局限。

示例：

> 原始想法是做个人舆情入口，减少社交媒体信息过载和情绪放大。但完整产品范围太大，所以我把项目缩成一个可严格验证的 evidence-research slice。
>
> 系统里有七种固定角色，角色绑定 Skills、Tool Set 和 Pydantic Schema。Forum Host 只能从固定注册表选角色，但能为不同任务创建多个临时实例。LangGraph 的 `StateGraph` 和 `Send` 负责动态 fan-out，列表 reducer 负责 fan-in。worker 不是在一个 Prompt 里模拟多角色，而是独立异步模型调用；我用 `asyncio.Event` barrier test 证明调用发生重叠，真实 provider smoke 里三个调用区间也重叠。
>
> worker 分两阶段：先输出结构化工具计划，程序检查权限、执行工具并生成 evidence ID，再让模型只基于这些结果总结。报告阶段又进一步缩小模型权限：程序从 evidence 生成 quote candidates，Citation Agent 只选 ID，不能自己复制引文；程序物化 `direct_quote` claim，再用 `ExactQuoteEvaluator` 检查完整 span。只有 supported 才能生成报告，其他 verdict 和 evaluator 故障都拒绝。Report Writer 也只排序 verified claim IDs，正文由程序渲染。
>
> 当前真实 adapter 只有 web search，数据库、多媒体、TikHub 和语义 claim evaluator 只是契约。系统证明的是文本支持和过程可审计，不证明来源真实或样本代表公众。

## 27.3 5 分钟

结构：

### 第一段：问题与范围

- 社媒信息过载和情绪放大；
- 原始简报/对话/报告愿景；
- 为什么缩为 bounded evidence research。

### 第二段：Agent 架构

- 七固定角色；
- 临时实例；
- Skills vs Tool Sets；
- Forum Host plan；
- LangGraph `Send` 和 reducers。

### 第三段：证据链

- 两阶段 worker；
- Tool Registry permission；
- evidence normalization；
- full-content hash；
- JSONL provenance。

### 第四段：支持门禁

- citation existence vs support；
- deterministic candidates；
- Citation Agent ID selection；
- claim type/scope；
- exact quote；
- fail-closed；
- deterministic report。

### 第五段：验证、困难与局限

- barrier test；
- real smoke；
- trace sanitization；
- run collision 和 Markdown injection；
- 当前只有 direct quote/web search/one round/one final claim；
- 下一步 semantic evaluator、source quality、representativeness。

---

## 28. 代码导读

建议按以下顺序阅读。

### 28.1 先看主动入口

1. `opinion_agent/cli.py`
2. `opinion_agent/research/factory.py`
3. `opinion_agent/research/service.py`

目标：理解一条 `research` 命令如何构建 service 并产生 artifacts。

### 28.2 再看 Agent 契约

1. `opinion_agent/agents/registry.py`
2. `opinion_agent/agents/skills.py`
3. `opinion_agent/agents/models.py`

目标：理解固定角色、Skills、Tools 和 structured output。

### 28.3 看 LangGraph

1. `opinion_agent/graph/state.py`
2. `opinion_agent/graph/research.py`
3. `tests/fakes.py`
4. `tests/test_research_graph.py`

目标：理解 `Send`、reducer、异步 overlap 和 canonical identity。

### 28.4 看工具与证据

1. `opinion_agent/tools/registry.py`
2. `opinion_agent/tools/search.py`
3. `opinion_agent/evidence/normalizer.py`
4. `opinion_agent/evidence/store.py`

目标：理解最小权限、provider parsing、stable ID 和 provenance。

### 28.5 看 claim gate

1. `opinion_agent/citations/models.py`
2. `opinion_agent/citations/evaluators.py`
3. `opinion_agent/citations/verifier.py`
4. `tests/test_claim_support.py`

目标：理解 claim type、scope、assessment contract 和 fail-closed。

### 28.6 看输出安全

1. `opinion_agent/reports/generator.py`
2. `opinion_agent/tracing/run_trace.py`
3. `tests/test_report.py`
4. `tests/test_run_trace.py`

目标：理解 deterministic rendering、sidecar、Markdown escape 和 secret redaction。

### 28.7 最后看演进

1. `docs/superpowers/specs/2026-06-05-personal-opinion-agent-design.md`
2. `docs/superpowers/specs/2026-06-06-evidence-research-agent-resume-scope-design.md`
3. `docs/superpowers/specs/2026-06-06-claim-evidence-support-gate-design.md`
4. `docs/verification/2026-06-07-real-provider-smoke.md`
5. `git log --oneline`

目标：理解范围如何收缩，以及真实运行如何推动架构硬化。

---

## 29. 术语表

| 术语 | 含义 |
|---|---|
| LLM | Large Language Model，大语言模型 |
| Agent | 由模型参与决策并可调用工具的有状态执行系统 |
| Agentic workflow | 在固定流程中嵌入模型决策节点的工作流 |
| Tool Calling | 模型输出结构化工具调用意图，程序验证后执行 |
| Structured Output | 符合预定义 Schema 的模型输出 |
| Schema | 字段、类型、范围和不变量的结构化契约 |
| Pydantic | Python 运行时数据验证库 |
| Role | 固定的能力、Prompt、Skills、Tools 和 Schema 模板 |
| Instance | 某一轮中为具体 task 创建的角色执行对象 |
| Skill | 角色的行为方法和规则说明 |
| Tool Set | 角色可调用工具的权限白名单 |
| Least privilege | 只授予完成任务所需的最小权限 |
| StateGraph | LangGraph 的状态图抽象 |
| Node | 图中的处理步骤 |
| Edge | 节点之间的转移关系 |
| `Send` | 根据运行时状态动态创建分支的 LangGraph 原语 |
| fan-out | 将一个计划拆成多个并发分支 |
| fan-in | 将多个分支结果汇合 |
| Reducer | 定义并发状态更新如何合并的函数 |
| Async concurrency | 多个 I/O 任务交错推进并发生时间重叠 |
| Parallelism | 多个计算在同一时刻实际并行执行 |
| Provenance | 数据来源和处理链的可追溯信息 |
| Evidence | 已持久化的来源记录或片段 |
| Evidence ID | evidence 的稳定内容身份 |
| Claim | 可独立验证的报告断言 |
| Citation | claim 对 evidence ID 的引用 |
| Support | evidence 是否在声明类型和 scope 下支持 claim |
| Scope | claim 的平台、时间窗和 sample 边界 |
| Direct quote | 与来源文本完全一致的直接引文 |
| Semantic evaluator | 判断 paraphrase、事实、汇总或推断支持关系的评估器 |
| NLI | Natural Language Inference，自然语言推断 |
| Verdict | supported/unsupported/contradicted/indeterminate |
| Fail-closed | 只有明确通过才放行，未知或失败默认拒绝 |
| Sidecar | 与主报告并列保存的机器可读验证文件 |
| Trace | 记录执行事件、身份、时间和结果的轨迹 |
| Auditability | 事后能够检查决策和数据链 |
| Replayability | 能基于完整状态重放运行；本项目当前不具备完整能力 |
| Adapter | 将统一内部接口连接到具体 provider/API 的实现 |
| Fake adapter | 不用网络和密钥的确定性测试实现 |
| Smoke test | 验证真实集成基本能走通的轻量测试 |
| Prompt injection | 不可信文本试图影响模型指令或工具行为 |
| Identity | 系统中 topic/task/role/evidence/claim/run 的规范身份 |
| Atomic replace | 先写临时文件，再整体替换单个目标文件 |
| Idempotency | 重复执行相同操作不会产生额外副作用 |
| Content-addressed ID | 由内容或内容 identity 派生的标识符 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| Abstention | evaluator 在能力不足时明确不判断 |
| Calibration | 预测置信与实际正确率之间的一致程度 |
| Representativeness | sample 对目标总体的代表程度 |

---

## 30. 面试前自检清单

能否不看代码回答：

- 为什么原始愿景需要缩小？
- 当前主动路径与历史原型怎么区分？
- Agent 与 workflow 的区别是什么？
- 七种角色分别是什么，哪些真实可执行？
- Skill 和 Tool Set 的区别是什么？
- 为什么角色固定、实例临时？
- LangGraph 图里究竟有哪些节点？
- 为什么 citation/report 在图外？
- `Send` 和 reducer 分别做什么？
- 如何证明 worker LLM 调用并发？
- 两阶段 worker 防止了什么？
- Evidence ID 如何计算？
- 为什么 hash 完整原文而存储截断文本？
- provider metadata 为什么嵌套？
- citation existence 与 support 有什么区别？
- 四种 claim type 是什么？
- scope 为什么必要？
- Citation Agent 为什么只选 ID？
- `ExactQuoteEvaluator` 能做什么、不能做什么？
- fail-closed 包含哪些拒绝情况？
- supported 为什么不等于事实为真？
- Report Writer 为什么不能写正文？
- trace 如何脱敏？
- run ID collision 如何处理？
- 原子写入有什么局限？
- real smoke 证明什么、不证明什么？
- 当前最重要的三个局限是什么？
- 下一步工程扩展与研究问题分别是什么？

如果这些问题能用自己的语言回答，并能指出对应源码与测试，这个项目就不再只是 GitHub 上的一组文件，而是一个可以被技术追问的完整工程案例。
