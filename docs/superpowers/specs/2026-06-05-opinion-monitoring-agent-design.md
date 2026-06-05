# Opinion Monitoring Agent MVP Design

Date: 2026-06-05

## Purpose

Build a local, runnable public-opinion monitoring agent for brand or institution monitoring. The first version should prove the full workflow from monitored target to report output without depending on the heavier `BettaFish` runtime, a production database, or a complex dashboard.

The agent should let a user define a target, keywords, and data sources, then collect relevant public items, normalize and deduplicate them, analyze sentiment and risk, and generate a Markdown daily report with clear warnings for high-risk items.

## Scope

### In Scope

- A new independent subproject at `D:\NLPIR\opinion_agent`.
- Local command-line execution.
- Configurable monitored target and keywords.
- Collector interface with at least one deterministic local/sample collector for testing.
- Optional integration point for public-source collection, such as TrendRadar output or simple news/search feeds.
- Normalized opinion item schema.
- Deduplication and relevance filtering.
- Rule-based sentiment and risk scoring for MVP reliability.
- Markdown daily report generation.
- JSONL local storage for collected and analyzed items.
- Automated tests for core pipeline behavior.

### Out of Scope For MVP

- Full web dashboard.
- Direct modification of `BettaFish` internals.
- Private database ingestion.
- Large-scale crawler operation.
- Automated posting to messaging platforms.
- Model-only classification that cannot be tested deterministically.

## Recommended Approach

Use a lightweight MVP that can later evolve into a standalone project.

This avoids inheriting `BettaFish` runtime complexity while still allowing ideas from `BettaFish` and `TrendRadar` to shape the design. The MVP should be useful with sample/local data first, then accept richer collectors as separate modules.

## Project Layout

```text
opinion_agent/
  README.md
  pyproject.toml
  opinion_agent/
    __init__.py
    __main__.py
    cli.py
    config.py
    models.py
    collectors/
      __init__.py
      base.py
      sample.py
      trendradar.py
    pipeline/
      __init__.py
      normalize.py
      dedupe.py
      relevance.py
      analyze.py
      run.py
    reports/
      __init__.py
      markdown.py
    storage/
      __init__.py
      jsonl.py
  tests/
    test_dedupe.py
    test_relevance.py
    test_analyze.py
    test_report.py
    test_pipeline.py
  examples/
    target.example.json
    sample_items.jsonl
  output/
    .gitkeep
```

## Data Model

Each collected item is normalized into one structure before analysis:

```json
{
  "id": "stable-id",
  "title": "Title",
  "url": "https://example.com/item",
  "source": "source-name",
  "published_at": "2026-06-05T12:00:00+08:00",
  "content": "Article body or summary",
  "matched_keywords": ["keyword"],
  "sentiment": "positive | neutral | negative",
  "risk_level": "low | medium | high",
  "summary": "One sentence summary"
}
```

The stable ID should be derived from URL when available; otherwise derive it from title, source, and published time.

## Data Flow

```text
target config
  -> collectors
  -> normalization
  -> deduplication
  -> relevance filtering
  -> sentiment and risk analysis
  -> local storage
  -> Markdown report
```

The pipeline should be callable from both CLI and tests. Core logic should not depend on terminal output, current working directory, or external network calls.

## CLI Behavior

MVP commands:

```powershell
python -m opinion_agent run --target examples\target.example.json
python -m opinion_agent report --target examples\target.example.json
```

`run` should collect, analyze, store, and write a report. `report` should regenerate a report from existing stored data when possible.

Expected report path pattern:

```text
output/reports/YYYY-MM-DD_<target-name>_opinion_daily.md
```

## Configuration

Target config should be JSON for MVP simplicity:

```json
{
  "name": "Sample Brand",
  "keywords": ["Sample Brand", "Sample Product"],
  "negative_keywords": ["complaint", "incident", "risk", "fraud", "refund"],
  "sources": ["sample"],
  "timezone": "Asia/Shanghai"
}
```

The config loader must validate required fields and return clear errors for invalid JSON, missing target name, or empty keyword lists.

## Analysis Rules

MVP analysis should be deterministic:

- `matched_keywords`: keywords that appear in title or content.
- `sentiment`: negative if negative keywords appear, positive if configured positive indicators appear, otherwise neutral.
- `risk_level`: high when negative keywords and target keywords co-occur in title or early content; medium when negative keywords appear only in content; low otherwise.
- `summary`: short extractive summary from title and first content sentence.

This can later be replaced or augmented by an LLM classifier, but deterministic rules should remain available for tests and fallback.

## Error Handling

- Invalid config should fail before collection and print a concise error.
- Collector failure should not crash the entire run if other collectors succeed; failed sources should be listed in the report metadata.
- Empty result sets should still generate a valid report stating no relevant items were found.
- Duplicate or malformed records should be skipped with counts reported.
- Network-backed collectors should use timeouts and return structured errors.

## Report Format

The Markdown report should include:

- Title with target name and report date.
- Executive summary.
- Risk overview counts: high, medium, low.
- Top risk items with source, title, URL, risk reason, and summary.
- Keyword hit summary.
- Source coverage and collector errors.
- Appendix with all relevant items.

The report must be useful without opening any separate UI.

## Testing Strategy

Automated tests should cover:

- Config loading and validation.
- Stable ID generation and deduplication.
- Keyword matching and relevance filtering.
- Sentiment and risk classification.
- Markdown report generation for normal, empty, and high-risk cases.
- End-to-end pipeline using sample data.

Primary verification command:

```powershell
cd D:\NLPIR\opinion_agent
python -m pytest tests -v
```

Manual smoke command:

```powershell
cd D:\NLPIR\opinion_agent
python -m opinion_agent run --target examples\target.example.json
```

## Delivery Criteria

The MVP is complete when:

- `opinion_agent` exists as an independent runnable subproject.
- A sample target config is included.
- The sample collector can run without network or API keys.
- A report is generated under `output/reports/`.
- Tests pass for the core pipeline.
- The README explains setup, run commands, and expected output.

## Future Extensions

- TrendRadar output collector.
- RSS/news-search collector.
- LLM-backed classification with deterministic fallback.
- Scheduled Windows task for daily runs.
- Web dashboard or Streamlit view.
- Notification adapters for email, Feishu, WeCom, or webhook.
- SQLite storage with trend comparison across days.

## Open Decisions For Implementation

- Use JSONL storage for MVP. SQLite is a future extension, not part of the first implementation plan.
- Use only standard library for the first version if practical; add dependencies only when they remove meaningful complexity.
- Keep collectors pluggable so TrendRadar and future crawlers do not affect pipeline tests.
