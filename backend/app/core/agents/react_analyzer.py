"""ReactAnalyzerAgent — multi-step article analysis with ReAct pattern."""
import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.agents.base import BaseAgent
from app.core.agents.fetcher import FetcherAgent
from app.core.agents.prompts import (
    ANALYZER_DEFAULT,
    ANALYZER_DIMENSION_PROMPT_TEMPLATE,
    ANALYZER_REFLECTION_PROMPT,
    ANALYZER_UNDERSTAND_PROMPT,
)
from app.core.tools.registry import dispatch_tool
from app.models import (
    AnalysisTraceStep,
    ComparisonReferenceEmbedded,
    QualityScoreDetail,
    ScoreEvidence,
    ToolCallDetail,
)
from app.models.quality_rubric import QualityRubric, get_default_rubric

# Max chars to send to LLM
MAX_CONTENT_CHARS = 12000

PRACTICAL_ARTICLE_TYPES = {"tutorial", "guide", "how-to"}
TECH_TOPIC_KEYWORDS = {"技术", "编程", "ai", "产品", "工具"}


class ReactAnalyzerAgent(BaseAgent):
    """React Agent for multi-step article analysis.

    Steps:
    1. Understand: Extract topic, core ideas, audience, type
    2. KB Comparison: Search similar articles in knowledge base
    3. Web Search: Search external similar articles
    4. Multidimensional Analysis: Parallel analysis of 4 dimensions
    5. Scoring: Score each dimension with reasoning
    6. Reflection: Validate and generate final report
    """

    def __init__(self, agent_config: Any | None = None) -> None:
        super().__init__(agent_config)
        self.trace: list[AnalysisTraceStep] = []
        self.step_index = 0
        self.parallel_group = 0

    def _add_trace_step(
        self,
        step_name: str,
        step_type: str,
        input_summary: str,
        output_summary: str,
        tool_calls: list[ToolCallDetail] | None = None,
        duration_ms: int = 0,
        raw_response: str = "",
        parsed_ok: bool = True,
        parallel_group: str | None = None,
        parallel_index: int | None = None,
    ) -> AnalysisTraceStep:
        """Add a trace step and return it."""
        step = AnalysisTraceStep(
            step_index=self.step_index,
            step_name=step_name,
            step_type=step_type,
            input_summary=input_summary[:500],
            output_summary=output_summary[:1000],
            tool_calls=tool_calls or [],
            duration_ms=duration_ms,
            timestamp=datetime.now(UTC),
            raw_response=raw_response[:2000],
            parsed_ok=parsed_ok,
            parallel_group=parallel_group,
            parallel_index=parallel_index,
        )
        self.trace.append(step)
        self.step_index += 1
        return step

    async def _get_llm(self) -> Any:
        """Get LLM client."""
        from app.core.llm.factory import get_llm_client_by_config_name

        config_name = getattr(self.agent_config, "model_config_name", "") if self.agent_config else ""
        if config_name:
            return await get_llm_client_by_config_name(config_name)

        from app.models import LLMModelConfig
        first = await LLMModelConfig.find_one(LLMModelConfig.is_active == True)  # noqa: E712
        if first:
            return await get_llm_client_by_config_name(first.name)

        raise RuntimeError("No LLM model config found.")

    def _get_active_rubric(self) -> QualityRubric:
        """Get the active quality rubric - now code-defined."""
        return get_default_rubric()

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.3,
        images: list[str] | None = None,
    ) -> tuple[str, bool]:
        """Call LLM and return (content, success)."""
        try:
            llm = await self._get_llm()
            # Some models (e.g., o3-mini, kimi moonshot-v1-32k) only support temperature=1
            # Check if the model requires fixed temperature
            model_name = getattr(llm, '_default_model', '').lower()
            print(f"[DEBUG] LLM model name: {model_name}, original temperature: {temperature}")
            if 'o3' in model_name or 'o1' in model_name or 'moonshot-v1-32k' in model_name:
                temperature = 1.0
                print(f"[DEBUG] Adjusted temperature to 1.0 for model {model_name}")
            print(f"[DEBUG] Calling llm.chat with temperature={temperature}")
            response = await llm.chat(messages, response_format=response_format, temperature=temperature, images=images)
            return response.content or "", True
        except Exception as e:
            print(f"[DEBUG] LLM call failed: {e}")
            return f"Error: {e}", False

    async def _step_understand(
        self,
        article_content: str,
        article_id: uuid.UUID | None = None,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """Step 1: Understand the article."""
        t_start = datetime.now(UTC)

        content = article_content[:MAX_CONTENT_CHARS]
        if len(article_content) > MAX_CONTENT_CHARS:
            content += "\n[内容已截断...]"

        use_vision = bool(images)

        system_prompt = ANALYZER_UNDERSTAND_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下文章：\n\n{content}"},
        ]

        raw_response, success = await self._call_llm(
            messages,
            response_format={"type": "json_object"},
            images=images if use_vision else None
        )
        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        result = {}
        if success:
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                success = False

        self._add_trace_step(
            step_name="理解文章",
            step_type="thought",
            input_summary=f"文章ID: {article_id}, 内容长度: {len(article_content)}",
            output_summary=json.dumps(result, ensure_ascii=False)[:500],
            duration_ms=duration_ms,
            raw_response=raw_response,
            parsed_ok=success,
        )

        return result

    async def _step_kb_comparison(
        self,
        article_content: str,
        article_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Step 2: Compare with knowledge base articles."""
        t_start = datetime.now(UTC)

        # Check if KB comparison is enabled
        analysis_config = getattr(self.agent_config, "analysis_config", None)
        if analysis_config and not getattr(analysis_config, "enable_kb_comparison", True):
            self._add_trace_step(
                step_name="知识库对比",
                step_type="observation",
                input_summary="KB comparison disabled",
                output_summary="Skipped",
                duration_ms=0,
            )
            return []

        # Call tool
        tool_result = await dispatch_tool(
            "search_similar_articles",
            {"article_content": article_content, "limit": 5},
        )

        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        results = []
        tool_calls = [ToolCallDetail(
            tool_name="search_similar_articles",
            input_params={"limit": 5},
            output_summary=tool_result[:200],
            success=not tool_result.startswith("Tool"),
        )]

        try:
            results = json.loads(tool_result)
            if not isinstance(results, list):
                results = []
        except json.JSONDecodeError:
            pass

        self._add_trace_step(
            step_name="知识库对比",
            step_type="tool_call",
            input_summary="搜索相似文章",
            output_summary=f"找到 {len(results)} 篇相似文章",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

        return results

    async def _step_web_search(
        self,
        article_content: str,
        topic: str,
        article_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Step 3: Search external similar articles."""
        t_start = datetime.now(UTC)

        # Check if web search is enabled
        analysis_config = getattr(self.agent_config, "analysis_config", None)
        enable_web_search = getattr(analysis_config, "enable_web_search", True)

        # Also check if Tavily key is configured
        from app.core.config import settings
        has_tavily = bool(settings.TAVILY_API_KEY)

        if not enable_web_search or not has_tavily:
            self._add_trace_step(
                step_name="外部搜索",
                step_type="observation",
                input_summary="Web search disabled or not configured",
                output_summary="Skipped",
                duration_ms=0,
            )
            return []

        # Generate search query from topic
        search_query = f"{topic} 文章"

        # Call web_search tool
        tool_result = await dispatch_tool(
            "web_search",
            {"query": search_query, "max_results": 5},
        )

        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        # Parse and save external references
        external_refs = []
        if not tool_result.startswith("web_search"):
            lines = tool_result.split("\n")
            for line in lines:
                if line.startswith("- ["):
                    # Parse: - [title](url): content
                    match = line.split("](", 1)
                    if len(match) == 2:
                        title_part = match[0][3:]  # Remove "- ["
                        url_content = match[1].split("):", 1)
                        if len(url_content) == 2:
                            url = url_content[0]
                            content_snippet = url_content[1].strip()

                            # Fetch full content using FetcherAgent for richer data
                            fetcher = FetcherAgent()
                            fetch_result = await fetcher.fetch_url(url)
                            full_content = fetch_result.get("content", content_snippet)
                            raw_html = fetch_result.get("raw_html", "")

                            # Save external reference
                            save_result = await dispatch_tool(
                                "save_external_reference",
                                {
                                    "url": url,
                                    "title": title_part,
                                    "content": full_content[:10000],
                                    "content_snippet": content_snippet[:500],
                                    "raw_html": raw_html,
                                    "source": "web_search",
                                    "search_query": search_query,
                                    "referencer_article_id": str(article_id) if article_id else None,
                                },
                            )

                            try:
                                save_data = json.loads(save_result)
                                external_refs.append({
                                    "id": save_data.get("id"),
                                    "url": url,
                                    "title": title_part,
                                    "content_snippet": content_snippet,
                                })
                            except json.JSONDecodeError:
                                pass

        tool_calls = [ToolCallDetail(
            tool_name="web_search",
            input_params={"query": search_query, "max_results": 5},
            output_summary=f"Found {len(external_refs)} external references",
            success=len(external_refs) > 0,
        )]

        self._add_trace_step(
            step_name="外部搜索",
            step_type="tool_call",
            input_summary=f"搜索查询: {search_query}",
            output_summary=f"找到 {len(external_refs)} 篇外部参考",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

        return external_refs

    async def _analyze_dimension(
        self,
        dimension: str,
        dimension_config: dict[str, Any],
        article_content: str,
        kb_articles: list[dict[str, Any]],
        external_refs: list[dict[str, Any]],
        understanding: dict[str, Any],
        parallel_index: int,
    ) -> dict[str, Any]:
        """Analyze a single dimension (for parallel execution)."""
        t_start = datetime.now(UTC)

        content = article_content[:8000]  # Shorter for dimension analysis

        criteria_text = "\n".join([
            f"- {c['min_score']}-{c['max_score']}: {c['description']}"
            for c in dimension_config.get("criteria", [])
        ])

        kb_context = ""
        if kb_articles:
            kb_context = "\n\n知识库参考文章:\n" + "\n".join([
                f"- {a.get('title', '')}: 质量分{a.get('quality_score', 'N/A')}"
                for a in kb_articles[:5]
            ])

        external_context = ""
        if external_refs:
            external_context = "\n\n外部参考文章:\n" + "\n".join([
                f"- {r.get('title', '')}: {r.get('content_snippet', '')[:100]}..."
                for r in external_refs
            ])

        # 判断是否为实操类文章
        article_type = understanding.get("article_type", "").lower()
        is_practical = article_type in PRACTICAL_ARTICLE_TYPES
        topic_category = understanding.get("topic_category", "").lower()
        is_tech_related = any(kw in topic_category for kw in TECH_TOPIC_KEYWORDS)

        practical_bonus_prompt = ""
        if is_practical and is_tech_related:
            practical_bonus_prompt = """

【本文疑似实操教程/技术指南 - 专业度加分说明】
本文被识别为实操类技术文章。评分时请特别注意：
- 如果包含原创代码、独特实战经验、详细步骤说明 → 原创性可上浮10-15分
- 如果步骤清晰、有实际可操作价值 → 内容深度可给60分以上（不按信息整合处理）
- 但如果只是简单罗列命令、复制粘贴文档内容、无个人经验分享 → 仍按低分处理"""

        system_prompt = ANALYZER_DIMENSION_PROMPT_TEMPLATE.format(
            dimension=dimension_config.get('description', dimension),
            criteria=criteria_text,
            practical_bonus=practical_bonus_prompt,
        )


        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下文章的{dimension_config.get('description', dimension)}维度：\n\n{content}{kb_context}{external_context}"},
        ]

        raw_response, success = await self._call_llm(messages, response_format={"type": "json_object"})
        if success:
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                result = {
                    "score": 50,
                    "reasoning": "解析失败: 无效的JSON响应",
                    "standard_matched": "",
                    "evidences": [],
                    "improvement_suggestions": [],
                }
        else:
            result = {
                "score": 50,
                "reasoning": f"分析失败: {raw_response}",
                "standard_matched": "",
                "evidences": [],
                "improvement_suggestions": [],
            }

        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        # Add trace step with parallel group
        self._add_trace_step(
            step_name=f"维度分析: {dimension}",
            step_type="conclusion",
            input_summary=f"分析维度: {dimension}",
            output_summary=f"得分: {result.get('score', 0)}",
            duration_ms=duration_ms,
            raw_response=raw_response[:1000],
            parsed_ok="score" in result,
            parallel_group="dimension_analysis",
            parallel_index=parallel_index,
        )

        return {
            "dimension": dimension,
            **result,
        }

    async def _step_multidimensional_analysis(
        self,
        article_content: str,
        kb_articles: list[dict[str, Any]],
        external_refs: list[dict[str, Any]],
        understanding: dict[str, Any],
        rubric: QualityRubric,
    ) -> list[dict[str, Any]]:
        """Step 4: Parallel multidimensional analysis."""
        t_start = datetime.now(UTC)

        dimensions = [
            {"name": d.name, "description": d.description, "weight": d.weight, "criteria": [
                {"min_score": c.min_score, "max_score": c.max_score, "description": c.description}
                for c in d.criteria
            ]}
            for d in rubric.dimensions
        ]

        # Check if parallel analysis is enabled
        react_config = getattr(self.agent_config, "react_config", None)
        parallel_enabled = getattr(react_config, "parallel_analysis", True)

        if parallel_enabled:
            # Run all dimensions in parallel
            tasks = [
                self._analyze_dimension(
                    dim["name"],
                    dim,
                    article_content,
                    kb_articles,
                    external_refs,
                    understanding,
                    i,
                )
                for i, dim in enumerate(dimensions)
            ]
            results = await asyncio.gather(*tasks)
        else:
            # Run sequentially
            results = []
            for i, dim in enumerate(dimensions):
                result = await self._analyze_dimension(
                    dim["name"],
                    dim,
                    article_content,
                    kb_articles,
                    external_refs,
                    understanding,
                    i,
                )
                results.append(result)

        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        return list(results)

    async def _step_scoring_with_reasoning(
        self,
        dimension_results: list[dict[str, Any]],
        rubric: QualityRubric,
    ) -> tuple[list[QualityScoreDetail], dict[str, float]]:
        """Step 5: Calculate final scores with detailed reasoning."""
        t_start = datetime.now(UTC)

        score_details = []
        scores = {}

        for result in dimension_results:
            dim_name = result.get("dimension", "")
            score = float(result.get("score", 0))
            weight = 0.20  # Default weight

            # Get weight from rubric
            dim = rubric.get_dimension(dim_name)
            if dim:
                weight = dim.weight

            weighted_score = score * weight
            scores[dim_name] = score

            # Build evidences
            evidences = []
            for e in result.get("evidences", []):
                if isinstance(e, dict):
                    evidences.append(ScoreEvidence(
                        quote=e.get("quote", ""),
                        context=e.get("context", ""),
                    ))

            score_details.append(QualityScoreDetail(
                dimension=dim_name,
                score=score,
                weight=weight,
                weighted_score=weighted_score,
                reasoning=result.get("reasoning", ""),
                standard_matched=result.get("standard_matched", ""),
                evidences=evidences,
                improvement_suggestions=result.get("improvement_suggestions", []),
            ))

        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        self._add_trace_step(
            step_name="综合评分",
            step_type="conclusion",
            input_summary=f"维度分析结果: {len(dimension_results)} 个维度",
            output_summary=f"总分: {sum(s.weighted_score for s in score_details):.2f}",
            duration_ms=duration_ms,
        )

        return score_details, scores

    async def _step_reflection(
        self,
        score_details: list[QualityScoreDetail],
        understanding: dict[str, Any],
    ) -> tuple[str, list[str]]:
        """Step 6: Reflection and final summary."""
        t_start = datetime.now(UTC)

        # Check if reflection is enabled
        react_config = getattr(self.agent_config, "react_config", None)
        if react_config and not getattr(react_config, "reflection_enabled", True):
            # Generate simple summary without LLM
            summary = f"文章主题: {understanding.get('topic', '')}。"
            suggestions = []
            for sd in score_details:
                suggestions.extend(sd.improvement_suggestions)

            t_end = datetime.now(UTC)
            duration_ms = int((t_end - t_start).total_seconds() * 1000)

            self._add_trace_step(
                step_name="反思验证",
                step_type="reflection",
                input_summary="Reflection disabled",
                output_summary="Generated simple summary",
                duration_ms=duration_ms,
            )

            return summary, suggestions[:5]

        # Build scores summary
        scores_text = "\n".join([
            f"- {sd.dimension}: {sd.score}/100 (权重{sd.weight}, 加权{sd.weighted_score:.2f})\n  依据: {sd.reasoning[:100]}..."
            for sd in score_details
        ])

        system_prompt = ANALYZER_REFLECTION_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"各维度评分结果:\n{scores_text}"},
        ]

        raw_response, success = await self._call_llm(messages, response_format={"type": "json_object"})

        result = {}
        if success:
            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError:
                success = False

        summary = result.get("analysis_summary", "")
        suggestions = result.get("improvement_suggestions", [])

        # If LLM failed, fallback to simple aggregation
        if not summary:
            summary = f"文章主题: {understanding.get('topic', '')}。"
            avg_score = sum(sd.score for sd in score_details) / max(len(score_details), 1)
            summary += f"整体质量评分: {avg_score:.1f}/100。"

        if not suggestions:
            for sd in score_details:
                suggestions.extend(sd.improvement_suggestions)
            suggestions = suggestions[:5]

        t_end = datetime.now(UTC)
        duration_ms = int((t_end - t_start).total_seconds() * 1000)

        self._add_trace_step(
            step_name="反思验证",
            step_type="reflection",
            input_summary=f"维度评分: {len(score_details)} 个",
            output_summary=summary[:200],
            duration_ms=duration_ms,
            raw_response=raw_response[:500],
            parsed_ok=success,
        )

        return summary, suggestions

    async def run(
        self,
        article_content: str,
        article_id: uuid.UUID | None = None,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the complete React analysis workflow.

        Args:
            article_content: The article content to analyze
            article_id: Optional article ID for tracking
            images: Optional list of image URLs for multimodal analysis

        Returns:
            Dict with analysis results matching ArticleAnalysis fields
        """
        t_start_total = datetime.now(UTC)

        # Reset trace
        self.trace = []
        self.step_index = 0

        # Get active rubric (code-defined)
        rubric = self._get_active_rubric()

        # Step 1: Understand
        understanding = await self._step_understand(article_content, article_id, images)

        # Step 2: KB Comparison
        kb_articles = await self._step_kb_comparison(article_content, article_id)

        # Step 3: Web Search
        topic = understanding.get("topic", "")
        external_refs = await self._step_web_search(article_content, topic, article_id)

        # Step 4: Multidimensional Analysis (parallel)
        dimension_results = await self._step_multidimensional_analysis(
            article_content, kb_articles, external_refs, understanding, rubric
        )

        # Step 5: Scoring
        score_details, scores = await self._step_scoring_with_reasoning(dimension_results, rubric)

        # Step 6: Reflection
        summary, suggestions = await self._step_reflection(score_details, understanding)

        # Calculate final score
        final_score = sum(sd.weighted_score for sd in score_details)

        # Build comparison references
        comparison_refs = []
        for kb in kb_articles[:5]:
            comparison_refs.append(ComparisonReferenceEmbedded(
                source="knowledge_base",
                kb_article_id=uuid.UUID(kb["article_id"]) if kb.get("article_id") else None,
                kb_article_title=kb.get("title"),
                quality_score=kb.get("quality_score"),
                similarity_score=kb.get("relevance_score", 0) / 100,
            ))
        for ext in external_refs:
            comparison_refs.append(ComparisonReferenceEmbedded(
                source="external",
                external_ref_id=uuid.UUID(ext["id"]) if ext.get("id") else None,
                external_url=ext.get("url"),
                external_title=ext.get("title"),
                similarity_score=0.5,  # Default for external refs (0-1 range)
            ))

        t_end_total = datetime.now(UTC)
        total_duration_ms = int((t_end_total - t_start_total).total_seconds() * 1000)

        # Build quality breakdown
        quality_breakdown = {
            "content_depth": scores.get("content_depth", 0),
            "readability": scores.get("readability", 0),
            "originality": scores.get("originality", 0),
            "ai_flavor": scores.get("ai_flavor", 0),
            "virality_potential": scores.get("virality_potential", 0),
            "image_content": scores.get("image_content", 0),
        }

        # Extract legacy fields from understanding with defaults
        structure_data = understanding.get("structure", {})
        style_data = understanding.get("style", {})

        return {
            "quality_score": round(final_score, 2),
            "quality_breakdown": quality_breakdown,
            "quality_score_details": [sd.model_dump() for sd in score_details],
            "comparison_references": [cr.model_dump() for cr in comparison_refs],
            "analysis_summary": summary,
            "improvement_suggestions": suggestions,
            "rubric_version": rubric.version if rubric else "",
            "analysis_duration_ms": total_duration_ms,
            "trace": [t.model_dump() for t in self.trace],
            # Legacy fields - now populated from analysis
            "hook_type": understanding.get("hook_type", ""),
            "framework": understanding.get("framework", ""),
            "emotional_triggers": understanding.get("emotional_triggers", []),
            "key_phrases": understanding.get("core_ideas", []),
            "keywords": understanding.get("key_entities", []),
            "structure": {
                "intro": structure_data.get("intro", "") if isinstance(structure_data, dict) else "",
                "body_sections": structure_data.get("body_sections", []) if isinstance(structure_data, dict) else [],
                "cta": structure_data.get("cta", "") if isinstance(structure_data, dict) else "",
            },
            "style": {
                "tone": style_data.get("tone", "") if isinstance(style_data, dict) else "",
                "formality": style_data.get("formality", "") if isinstance(style_data, dict) else "",
                "avg_sentence_length": style_data.get("avg_sentence_length", 0) if isinstance(style_data, dict) else 0,
            },
            "target_audience": understanding.get("target_audience", ""),
            "topic": understanding.get("topic", ""),
            "topic_category": understanding.get("topic_category", ""),
            "article_type": understanding.get("article_type", ""),
        }
