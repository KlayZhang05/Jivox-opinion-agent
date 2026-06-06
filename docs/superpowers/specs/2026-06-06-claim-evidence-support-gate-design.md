# Claim-Evidence Support Gate Design

Date: 2026-06-06
Status: Approved with requested changes incorporated

## Purpose

Upgrade report verification from "the cited evidence ID exists" to "the cited
evidence supports the claim."

This gate addresses a central failure mode in public-opinion analysis: a report
may cite a real source while inventing a comment, exaggerating a trend, or
drawing a conclusion that the source does not justify. Citation existence and
claim support are separate checks. Both must pass before a claim enters a
report.

The gate must remain conservative, auditable, provider-neutral, and usable
without a network connection.

## Scope

This slice includes:

- explicit separation between citation validation and semantic support
  validation;
- atomic report claims with stable claim IDs;
- explicit claim types and optional scope metadata;
- structured support assessments;
- exact verification of quoted evidence spans;
- an exact-quote evaluator for direct source spans;
- a protocol for later LLM or local NLI evaluators;
- fail-closed report generation;
- a machine-readable verification sidecar;
- deterministic tests and CLI examples.

This slice does not include:

- selecting or configuring a production LLM provider;
- measuring source credibility or source independence;
- deciding whether a sample represents the whole population;
- semantic verification of multi-claim conversation turns;
- TrendRadar ingestion;
- a real LangGraph execution graph.

Those concerns depend on this contract but are separate implementation slices.

## Design Principles

1. Citation existence is necessary but insufficient.
2. Every report claim is verified independently.
3. Evidence text remains data, never instructions to the evaluator.
4. Only an explicit `supported` verdict can pass.
5. Missing, malformed, uncertain, contradictory, or failed evaluation rejects
   the claim.
6. A support assessment is not trusted until its evidence references and
   quoted spans are checked deterministically.
7. The system never silently falls back from semantic verification to ID-only
   verification.
8. Verification artifacts are preserved for audit and replay.

## Claim Contract

Every report claim must use this shape:

```json
{
  "claim_id": "claim-001",
  "claim_type": "direct_quote",
  "text": "The city published a limited route adjustment.",
  "scope": {
    "platform": "city_website",
    "time_window": {
      "start": "2026-06-06T00:00:00Z",
      "end": "2026-06-06T23:59:59Z"
    },
    "sample": "single official notice"
  },
  "evidence_ids": ["ev-001"]
}
```

Initial claim types:

- `direct_quote`: `text` is a verbatim span from cited evidence.
- `factual_statement`: a fact expressed directly or by faithful paraphrase.
- `opinion_summary`: a bounded synthesis of opinions in a declared sample.
- `analytic_inference`: an interpretation or conclusion derived from evidence.

Rules:

- `claim_id` is a non-empty string and unique within a report.
- `claim_type` is one of the four initial values.
- `text` is a non-empty, atomic statement.
- For `direct_quote`, `text` is the exact source span, not prose surrounding or
  interpreting the quotation.
- `scope` is optional. When present, it is an object containing any of:
  - `platform`: a non-empty string naming the bounded platform or source domain;
  - `time_window`: an object with optional ISO-8601 `start` and `end` strings;
  - `sample`: a non-empty string describing the evidence sample represented.
- `evidence_ids` is a non-empty list of unique, non-empty strings.
- One claim must not combine independently verifiable assertions.
- A report input with duplicate claim IDs is invalid.
- Scope metadata is preserved through verification and report artifacts. The
  first implementation validates its shape but does not infer or expand it.

The report writer or future claim-decomposition node owns claim atomization.
The support gate does not split prose because silent splitting would make audit
identity unstable.

The first implementation supports only `direct_quote`. The exact-quote
evaluator returns `indeterminate` for `factual_statement`, `opinion_summary`,
and `analytic_inference`. A semantic evaluator is required to assess those
types.

## Support Assessment Contract

```python
ClaimType = Literal[
    "direct_quote",
    "factual_statement",
    "opinion_summary",
    "analytic_inference",
]

SupportVerdict = Literal[
    "supported",
    "unsupported",
    "contradicted",
    "indeterminate",
]


@dataclass(frozen=True)
class EvidenceSpan:
    evidence_id: str
    quote: str


@dataclass(frozen=True)
class SupportAssessment:
    claim_id: str
    claim_type: ClaimType
    verdict: SupportVerdict
    reason: str
    scope: Mapping[str, Any] | None = None
    supporting_spans: tuple[EvidenceSpan, ...] = ()
    contradicting_spans: tuple[EvidenceSpan, ...] = ()
    evaluator: str = ""
    evaluator_version: str = ""
```

Verdict meanings:

- `supported`: the cited evidence supports the claim within its declared
  `claim_type` and `scope`.
- `unsupported`: the evidence is relevant but insufficient for the claim.
- `contradicted`: at least one cited source directly conflicts with the claim.
- `indeterminate`: the evaluator cannot make a reliable decision.

`supported` does not expand the claim's scope. For example, support for a
statement scoped to one platform and one time window is not support for all
platforms or a longer period. Preserving scope is mandatory even when the first
implementation cannot reason about it.

Uncalibrated numeric confidence must not control release in this slice.

## Evaluator Boundary

```python
class SupportEvaluator(Protocol):
    def assess(
        self,
        claim: ClaimInput,
        evidence: Sequence[Mapping[str, Any]],
    ) -> SupportAssessment:
        ...
```

The evaluator receives only the evidence records cited by the claim, in the
same order as `evidence_ids`. It must not retrieve new sources or mutate the
store.

Two evaluator modes are required by the architecture:

### Exact Quote Evaluator

The first runnable implementation provides a deterministic
`ExactQuoteEvaluator`. It returns `supported` only when:

- `claim_type` is `direct_quote`; and
- the complete claim `text` occurs as an exact span in cited evidence content.

For other claim types it returns `indeterminate`, even when words overlap.
Paraphrases, aggregations, inferred absence, trend language, opinion summaries,
analytic inferences, and population-level claims therefore require a configured
semantic evaluator.

This mode is intentionally narrow. It provides a zero-cost, reproducible
baseline without pretending that keyword overlap is semantic verification.

### Semantic Evaluator Adapter

The same protocol supports a later LLM or local NLI adapter. The adapter must
return the structured assessment above. Provider selection and credentials are
deferred to a separate design decision.

Evaluator exceptions, timeouts, malformed output, and unknown verdicts are
converted to `indeterminate` and rejected.

## Deterministic Verification Pipeline

The public verification API is split explicitly:

```python
verify_citations(claim, evidence_store) -> CitationVerificationResult

verify_claim_support(
    claim,
    evidence_store,
    support_evaluator,
) -> ClaimVerificationResult
```

`verify_citations` is allowed for workflows that make no semantic-support
claim, such as the current bounded conversation transcript.

The ambiguous existing name `verify_claim` is removed from internal consumers
and public exports. It must not remain as an alias because callers could mistake
citation-only validation for semantic verification.

`verify_claim_support` performs these steps:

1. Validate the claim structure.
2. Resolve all cited evidence records in requested order.
3. Reject missing evidence without calling the evaluator.
4. Call the evaluator with the claim and resolved evidence bundle.
5. Validate the assessment structure and matching `claim_id`, `claim_type`, and
   `scope`.
6. Preserve the claim's declared `claim_type` and `scope`.
7. Ensure every assessment evidence ID belongs to the claim's cited IDs.
8. Ensure every quoted span occurs in the corresponding evidence content.
9. Enforce verdict invariants:
   - `supported` requires at least one valid supporting span;
   - `supported` cannot include contradicting spans;
   - `contradicted` requires at least one valid contradicting span;
   - all non-`supported` verdicts reject the claim.
10. Return structured errors and the assessment.

Quoted-span matching normalizes line endings only. It does not collapse
whitespace, rewrite punctuation, translate text, or use fuzzy matching.

## Evidence Store Change

`EvidenceStore` gains:

```python
get_many(evidence_ids: Sequence[str]) -> list[dict[str, Any]]
```

The method:

- preserves requested order;
- rejects duplicate requested IDs;
- raises an explicit error listing missing IDs;
- returns independent mappings so evaluators cannot mutate persisted records.

The store remains append-only JSONL in this slice.

## Report Integration

Reports use `verify_claim_support`; they never call citation-only verification.
The core report-generation API requires a `SupportEvaluator` argument with no
implicit default. The CLI explicitly constructs the exact-quote evaluator
for this slice, so the sample command remains runnable but cannot bypass the
support gate. The sample claim is updated to a `direct_quote` with a directly
verifiable source span.

The report pipeline is:

```text
claims
  -> claim shape validation
  -> citation resolution
  -> support evaluator
  -> deterministic assessment validation
  -> all claims supported?
       yes -> render Markdown and verification JSON
       no  -> write nothing and return explicit errors
```

All claims must pass before any report artifact is written. Partial reports are
not emitted silently.

The Markdown report shows:

- each atomic claim;
- supporting evidence IDs;
- exact supporting excerpts;
- source name, source type, title, and URL;
- a citation-and-support gate statement.

The sidecar `<report-name>_verification.json` stores:

- schema version;
- topic;
- claim inputs;
- claim types and declared scope metadata;
- validated assessments;
- evaluator identity and version.

The sidecar must not store API keys, hidden reasoning, or provider request
headers.

## Conversation Boundary

The current conversation session treats an entire assistant analysis turn as
one claim. A turn may contain several factual and interpretive statements, so
applying one semantic verdict to the whole turn would give false assurance.

For this slice:

- conversation analysis turns continue to use `verify_citations`;
- the README identifies this as citation validation, not semantic support;
- a later slice will add explicit atomic claims to assistant turns and evaluate
  each claim independently.

## Error Handling

The system fails closed for:

- malformed claim input;
- unknown claim types or malformed scope metadata;
- duplicate claim IDs;
- missing or duplicate evidence IDs;
- missing evidence records;
- evaluator exceptions or timeouts;
- malformed assessments;
- assessment claim-ID mismatch;
- evidence references outside the cited bundle;
- quoted spans absent from stored evidence;
- `unsupported`, `contradicted`, or `indeterminate` verdicts.

Errors name the claim ID and failure class without exposing secrets or full
provider payloads.

## Security And Hallucination Controls

- Evidence content is delimited and treated as untrusted data by future model
  adapters.
- Assessment references are constrained to the cited evidence bundle.
- Exact quote verification prevents an evaluator from inventing comments or
  source passages.
- Provider output never writes directly to report files.
- The report renderer consumes only validated assessments.
- A real source with an unrelated passage does not pass merely because its ID
  exists.

This gate does not prove source truthfulness. Source reliability, coordination,
bot detection, representativeness, and cross-source corroboration require
separate analysis.

## Testing Strategy

Tests must cover:

- valid citation-only verification;
- unknown evidence rejection before evaluator invocation;
- ordered `get_many` retrieval and missing-ID errors;
- exact `direct_quote` acceptance;
- non-direct claim types returning `indeterminate` under the exact-quote
  evaluator;
- claim scope validation and preservation;
- unrelated evidence rejection;
- contradicted claim rejection;
- indeterminate claim rejection;
- evaluator exception rejection;
- malformed assessment rejection;
- invented supporting quote rejection;
- assessment reference outside cited IDs rejection;
- duplicate claim ID rejection at report level;
- no report or sidecar written when any claim fails;
- Markdown and sidecar output when all claims pass;
- current conversation behavior remaining citation-only.

Tests use deterministic evaluators and local evidence. They require no network,
API key, LangGraph installation, or model provider.

## Acceptance Criteria

This implementation slice is complete when:

1. Citation-only and semantic-support APIs are separate and named explicitly.
2. Reports require semantic-support verification and cannot silently bypass it.
3. Only `supported` assessments with verified source spans enter reports.
4. Unknown, unsupported, contradicted, indeterminate, malformed, or failed
   assessments prevent all report artifacts.
5. The exact-quote evaluator supports reproducible `direct_quote` reports and
   returns `indeterminate` for all other claim types.
6. A provider-neutral evaluator protocol exists for later LLM or NLI adapters.
7. Successful reports preserve claim type and scope in Markdown and a
   machine-readable verification sidecar.
8. Existing briefing and bounded-conversation behavior remains operational.
9. The full test suite and CLI smoke tests pass.

## Follow-On Slices

1. Select and implement a production semantic evaluator provider.
2. Add evaluator prompt-injection tests and model-output conformance tests.
3. Add source reliability and cross-source corroboration gates.
4. Add atomic claims and semantic verification to bounded conversations.
5. Add the read-only TrendRadar collector adapter and evidence identity policy.
6. Wrap deterministic services in a real LangGraph runtime with checkpointed
   state and temporary research sub-agents.
