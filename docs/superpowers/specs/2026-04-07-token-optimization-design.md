# Token Usage Optimization Design

## Problem Statement

Current LLM token consumption is high due to two main architectural patterns:

1. **ReactAnalyzerAgent performs 5 parallel LLM calls for dimension analysis**, each sending the full article text (up to 8,000 chars) + context. This means the same article is read by the LLM 5 times.
2. **FetcherAgent invokes an LLM just to validate whether HTTP-fetched content is real article text**, adding an unnecessary LLM call to every URL fetch.

## Goals

- **P0:** Reduce ReactAnalyzerAgent dimension analysis from 5 LLM calls to 1 structured call without degrading output quality.
- **P1:** Remove LLM-based content validation from FetcherAgent and replace it with fast heuristic rules.

## P0: Single-Call Multi-Dimension Analysis

### Current Flow

`_step_multidimensional_analysis` spawns 5 parallel `_analyze_dimension` calls, one per rubric dimension:
- `content_depth`
- `readability`
- `originality`
- `ai_flavor`
- `virality_potential`

Each call sends:
- `article_content[:8000]`
- KB articles context
- External references context
- Dimension-specific criteria

### New Flow

1. Add a new prompt `ANALYZER_ALL_DIMENSIONS_PROMPT_TEMPLATE` in `prompts.py` that inlines all 5 dimensions, their weights, and criteria.
2. Add `_analyze_all_dimensions` in `react_analyzer.py` that makes a single `llm.chat(..., response_format={"type": "json_object"})` call.
3. Rewrite `_step_multidimensional_analysis` to call `_analyze_all_dimensions` once, then map the returned JSON into the same 5-item list format that downstream scoring expects.
4. For trace compatibility, emit 5 trace steps (one per dimension) from the single parsed result.

### Output JSON Schema期望

```json
{
  "dimensions": [
    {
      "dimension": "content_depth",
      "score": 82,
      "reasoning": "...",
      "standard_matched": "...",
      "evidences": [{"quote": "...", "context": "..."}],
      "improvement_suggestions": ["..."]
    },
    ...
  ]
}
```

### Fallback

If the JSON parse fails or a dimension is missing, return the default fallback structure for that dimension (score 50, empty evidence, etc.) to avoid breaking the overall analysis pipeline.

## P1: Heuristic Content Validation in FetcherAgent

### Current Flow

`fetch_url` -> HTTP fetch -> `_is_content_valid` -> LLM call -> if NO -> Playwright fallback.

### New Flow

`fetch_url` -> HTTP fetch -> `_is_content_valid_heuristic` -> if False -> Playwright fallback.

No LLM is involved in the validity check.

### Heuristic Rules

```python
def _is_content_valid_heuristic(self, content: str) -> bool:
    stripped = content.strip()
    if len(stripped) < 200:
        return False
    if len(stripped) >= 1500:
        return True
    paragraphs = [p for p in stripped.split("\n\n") if len(p.strip()) > 50]
    sentences = re.split(r"[。！？.!?]", stripped)
    return len(paragraphs) >= 2 and len(sentences) >= 5
```

- Short content (< 200 chars) = invalid (likely skeleton page / nav / ad)
- Long content (>= 1500 chars) = valid (HTTP already got substantial text)
- Medium content uses paragraph + sentence density as a sanity check

## Files to Modify

- `backend/app/core/agents/prompts.py` — add unified multi-dimension prompt
- `backend/app/core/agents/react_analyzer.py` — implement single-call analysis, update `_step_multidimensional_analysis`
- `backend/app/core/agents/fetcher.py` — replace `_is_content_valid` with heuristic version

## Testing

- Add/update unit tests for `_analyze_all_dimensions` parsing and fallback
- Add/update tests for `_is_content_valid_heuristic` covering short, medium, and long content
- Run existing `test_analyzer_agent.py`, `test_fetcher_agent.py`, integration tests to verify backward compatibility

## Non-Goals

- Changing rubric definitions or scoring weights
- Changing OrchestratorAgent workflow (that is a separate optimization)
- Adding a tiered model strategy (light vs heavy models)
