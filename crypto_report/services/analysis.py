from __future__ import annotations

import json
import re
from typing import Any, Dict, List


class AIAnalysisService:
    """Generate narrative analysis with AI-first, rule-based fallback."""

    def __init__(self, config, http, logger, sentiment_service) -> None:
        self.config = config
        self.http = http
        self.logger = logger
        self.sentiment_service = sentiment_service

    def get_ai_analysis(
        self,
        fear_greed_index: Dict[str, Any],
        crypto_news: List[Dict[str, Any]],
        market_overview: Dict[str, Any],
        technical_context: Dict[str, Any] | None = None,
        macro_context: Dict[str, Any] | None = None,
        defi_overview: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        sentiment_counts, news_keywords, news_tag_summary, news_event_summary = self._collect_news_features(crypto_news)
        event_watchlist = self.build_event_watchlist(crypto_news)
        weekly_ai_trend = self.analyze_ai_weekly_trend(
            fear_greed_index,
            market_overview,
        )
        sentiment_composite = self.build_sentiment_composite(
            fear_greed_index,
            market_overview,
            sentiment_counts,
        )
        fallback = self._build_rule_based_analysis(
            fear_greed_index,
            market_overview,
            technical_context or {},
            macro_context or {},
            defi_overview or {},
            sentiment_counts,
            news_keywords,
            news_tag_summary,
            news_event_summary,
            event_watchlist,
            weekly_ai_trend,
            sentiment_composite,
        )

        ai_result = self._generate_deepseek_analysis(
            fear_greed_index,
            crypto_news,
            market_overview,
            technical_context or {},
            macro_context or {},
            defi_overview or {},
            sentiment_counts,
            weekly_ai_trend,
        )
        if not ai_result:
            return fallback

        analysis = dict(fallback)
        analysis.update(ai_result)
        analysis["sentiment_summary"] = sentiment_counts
        analysis["news_tag_summary"] = news_tag_summary
        analysis["news_event_summary"] = news_event_summary
        analysis["event_watchlist"] = event_watchlist
        analysis["sentiment_composite"] = sentiment_composite
        if weekly_ai_trend:
            analysis["weekly_trend"] = weekly_ai_trend
            analysis.setdefault(
                "trend_enhanced_analysis",
                self.generate_ai_trend_enhanced_analysis(weekly_ai_trend),
            )
        return analysis

    @staticmethod
    def _collect_news_features(
        crypto_news: List[Dict[str, Any]],
    ) -> tuple[Dict[str, int], List[str], Dict[str, int], Dict[str, int]]:
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        news_keywords: List[str] = []
        news_tag_summary: Dict[str, int] = {}
        news_event_summary: Dict[str, int] = {}
        for item in crypto_news:
            sentiment = item.get("sentiment", "")
            if "利好" in sentiment or "积极" in sentiment:
                sentiment_counts["positive"] += 1
            elif "利空" in sentiment or "谨慎" in sentiment:
                sentiment_counts["negative"] += 1
            else:
                sentiment_counts["neutral"] += 1

            title = item.get("title", "")
            tags = item.get("tags") or []
            if "比特币" in title:
                news_keywords.append("比特币")
            elif "以太坊" in title:
                news_keywords.append("以太坊")
            elif "监管" in title or "政策" in title:
                news_keywords.append("监管")
            elif "DeFi" in title or "Layer2" in title:
                news_keywords.append("技术")
            for tag in tags:
                tag_text = str(tag).strip()
                if not tag_text:
                    continue
                news_keywords.append(tag_text)
                news_tag_summary[tag_text] = news_tag_summary.get(tag_text, 0) + 1
                event_label = AIAnalysisService._map_tag_to_event_theme(tag_text)
                if event_label:
                    news_event_summary[event_label] = news_event_summary.get(event_label, 0) + 1
        return sentiment_counts, news_keywords, news_tag_summary, news_event_summary

    @staticmethod
    def _map_tag_to_event_theme(tag: str) -> str:
        return {
            "监管": "监管与合规",
            "ETF/机构": "机构资金",
            "安全事件": "安全风险",
            "DeFi": "DeFi生态",
            "交易所": "交易平台",
            "链上/挖矿": "链上与矿业",
            "技术升级": "技术进展",
        }.get(str(tag).strip(), "")

    def build_event_watchlist(self, crypto_news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        watchlist: List[Dict[str, Any]] = []
        max_items = getattr(self.config, "max_event_watch_items", 6)
        for item in crypto_news:
            tags = item.get("tags") or []
            theme = ""
            for tag in tags:
                theme = self._map_tag_to_event_theme(str(tag))
                if theme:
                    break
            if not theme:
                continue
            watchlist.append(
                {
                    "theme": theme,
                    "title": str(item.get("title", "")).strip(),
                    "time": str(item.get("time", "")).strip(),
                    "impact": str(item.get("impact", "")).strip(),
                    "source": str(item.get("source", "")).strip(),
                }
            )
        deduped: List[Dict[str, Any]] = []
        seen = set()
        for item in watchlist:
            key = (item["theme"], item["title"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:max_items]

    @staticmethod
    def summarize_news_focus(news_tag_summary: Dict[str, int]) -> str:
        if not news_tag_summary:
            return "当前新闻面缺少清晰主线，更多以零散事件驱动为主。"
        top_tags = sorted(
            news_tag_summary.items(),
            key=lambda item: (-item[1], item[0]),
        )[:2]
        labels = [str(tag) for tag, _ in top_tags if tag]
        if not labels:
            return "当前新闻面缺少清晰主线，更多以零散事件驱动为主。"
        if len(labels) == 1:
            return f"新闻主线集中在{labels[0]}，相关事件对短线情绪影响更直接。"
        return f"新闻主线集中在{labels[0]}与{labels[1]}，说明资金更关注政策、资金或事件催化。"

    def _build_rule_based_analysis(
        self,
        fear_greed_index: Dict[str, Any],
        market_overview: Dict[str, Any],
        technical_context: Dict[str, Any],
        macro_context: Dict[str, Any],
        defi_overview: Dict[str, Any],
        sentiment_counts: Dict[str, int],
        news_keywords: List[str],
        news_tag_summary: Dict[str, int],
        news_event_summary: Dict[str, int],
        event_watchlist: List[Dict[str, Any]],
        weekly_ai_trend: Dict[str, Any],
        sentiment_composite: Dict[str, Any],
    ) -> Dict[str, Any]:
        fgi_value = fear_greed_index.get("value", 50)
        sentiment_analysis = self.sentiment_service.get_sentiment_analysis(fear_greed_index)
        sentiment_deep_analysis = self.build_sentiment_deep_analysis(
            sentiment_analysis,
            market_overview,
        )
        financial_analyst = self.build_financial_analyst_view(
            sentiment_analysis,
            market_overview,
            sentiment_counts,
            news_tag_summary,
            weekly_ai_trend,
            macro_context,
            defi_overview,
        )
        news_focus_summary = self.summarize_news_focus(news_tag_summary)
        analysis = {
            "market_overview": self.generate_dynamic_market_overview(
                fgi_value,
                market_overview,
                sentiment_counts,
                news_focus_summary,
                weekly_ai_trend,
                macro_context,
                defi_overview,
            ),
            "technical_analysis": self.generate_dynamic_technical_analysis(
                fgi_value,
                technical_context,
                weekly_ai_trend,
                macro_context,
                defi_overview,
            ),
            "risk_assessment": self.generate_dynamic_risk_assessment(
                fgi_value,
                sentiment_counts,
                macro_context,
                defi_overview,
            ),
            "trading_signals": self.generate_dynamic_trading_signals(
                fgi_value,
                news_keywords,
                macro_context,
                defi_overview,
            ),
            "sentiment_summary": sentiment_counts,
            "sentiment_composite": sentiment_composite,
            "news_tag_summary": news_tag_summary,
            "news_event_summary": news_event_summary,
            "event_watchlist": event_watchlist,
            "sentiment_deep_analysis": sentiment_deep_analysis,
            "financial_analyst": financial_analyst,
        }
        if weekly_ai_trend:
            analysis["weekly_trend"] = weekly_ai_trend
            analysis["trend_enhanced_analysis"] = (
                self.generate_ai_trend_enhanced_analysis(weekly_ai_trend)
            )
        return analysis

    def _has_deepseek_config(self) -> bool:
        api_key = (self.config.deepseek_api_key or "").strip()
        return bool(api_key and api_key != "replace-me")

    def _deepseek_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.deepseek_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    def build_sentiment_composite(
        self,
        fear_greed_index: Dict[str, Any],
        market_overview: Dict[str, Any],
        sentiment_counts: Dict[str, int],
    ) -> Dict[str, Any]:
        fgi_value = int(fear_greed_index.get("value", 50) or 50)
        market_change = float(market_overview.get("market_cap_change_percentage_24h_usd", 0) or 0)
        btc_dominance_daily_change = market_overview.get("btc_dominance_daily_change")
        total_news = sum(sentiment_counts.values())
        if total_news > 0:
            news_score = (
                (
                    sentiment_counts.get("positive", 0)
                    + sentiment_counts.get("neutral", 0) * 0.5
                ) / total_news
            ) * 100
        else:
            news_score = 50.0

        market_score = self._clamp(50 + market_change * 8, 0, 100)
        score = fgi_value * 0.5 + news_score * 0.3 + market_score * 0.2

        drivers: List[str] = []
        if fgi_value <= 25:
            drivers.append(f"恐惧贪婪指数处于低位（{fgi_value}），市场情绪偏防御。")
        elif fgi_value >= 70:
            drivers.append(f"恐惧贪婪指数回升至{fgi_value}，风险偏好明显修复。")
        else:
            drivers.append(f"恐惧贪婪指数为{fgi_value}，情绪仍处于常态区间。")

        if market_change >= 2:
            drivers.append(f"总市值24小时上涨{market_change:.2f}%，短线资金偏积极。")
        elif market_change <= -2:
            drivers.append(f"总市值24小时下跌{abs(market_change):.2f}%，盘面仍偏谨慎。")
        else:
            drivers.append(f"总市值24小时变化{market_change:+.2f}%，方向性仍待确认。")

        if total_news > 0:
            positive = sentiment_counts.get("positive", 0)
            negative = sentiment_counts.get("negative", 0)
            if positive > negative:
                drivers.append(f"新闻面以正面/中性为主（正面{positive}，负面{negative}）。")
            elif negative > positive:
                drivers.append(f"新闻面偏谨慎（负面{negative}，正面{positive}）。")
            else:
                drivers.append(f"新闻情绪相对均衡（正面{positive}，负面{negative}）。")

        if isinstance(btc_dominance_daily_change, (int, float)):
            dominance_change = float(btc_dominance_daily_change)
            if dominance_change >= 0.3:
                score -= min(6.0, dominance_change * 8)
                drivers.append(f"BTC主导率日升{dominance_change:+.2f}pct，资金偏向防御主线。")
            elif dominance_change <= -0.3:
                score += min(6.0, abs(dominance_change) * 8)
                drivers.append(f"BTC主导率日降{dominance_change:+.2f}pct，风险偏好向山寨扩散。")

        final_score = int(round(self._clamp(score, 0, 100)))
        if final_score <= 25:
            label = "极度防御"
            summary = "综合信号偏弱，短线仍以防守和等待确认为主。"
        elif final_score <= 45:
            label = "偏防御"
            summary = "情绪修复尚不稳固，适合控制仓位、优先观察主流资产。"
        elif final_score <= 60:
            label = "中性平衡"
            summary = "多空信号相对均衡，市场仍在寻找下一阶段方向。"
        elif final_score <= 75:
            label = "风险偏好回升"
            summary = "情绪和盘面同步改善，可关注量价是否继续确认。"
        else:
            label = "偏热"
            summary = "风险偏好较强，但需警惕情绪过热后的回撤。"

        return {
            "score": final_score,
            "label": label,
            "summary": summary,
            "drivers": drivers[:4],
        }

    def _build_deepseek_payload(
        self,
        fear_greed_index: Dict[str, Any],
        crypto_news: List[Dict[str, Any]],
        market_overview: Dict[str, Any],
        technical_context: Dict[str, Any],
        macro_context: Dict[str, Any],
        defi_overview: Dict[str, Any],
        sentiment_counts: Dict[str, int],
        weekly_ai_trend: Dict[str, Any],
    ) -> Dict[str, Any]:
        news_digest = [
            {
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "sentiment": item.get("sentiment", ""),
                "source": item.get("source", ""),
            }
            for item in crypto_news[:5]
        ]
        prompt_context = {
            "fear_greed_index": {
                "value": fear_greed_index.get("value", 50),
                "classification": fear_greed_index.get("classification", "中性"),
                "daily_change": fear_greed_index.get("daily_change"),
                "weekly_change": fear_greed_index.get("weekly_change"),
                "monthly_change": fear_greed_index.get("monthly_change"),
            },
            "market_overview": {
                "market_cap_change_percentage_24h_usd": market_overview.get(
                    "market_cap_change_percentage_24h_usd",
                    0,
                ),
                "btc_dominance": market_overview.get(
                    "market_cap_percentage",
                    {},
                ).get("btc", 0),
                "total_market_cap": market_overview.get("total_market_cap", 0),
                "total_volume": market_overview.get("total_volume", 0),
            },
            "news_sentiment_summary": sentiment_counts,
            "technical_context": technical_context,
            "macro_context": macro_context,
            "defi_overview": defi_overview,
            "weekly_trend": weekly_ai_trend,
            "top_news": news_digest,
        }
        return {
            "model": "deepseek-chat",
            "stream": False,
            "temperature": 0.4,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是数字货币日报分析助手。"
                        "请基于提供的数据生成简洁、专业、偏交易和风控视角的中文分析。"
                        "输出风格要求：避免空泛表述，优先使用'情绪修复'、'资金偏防御'、"
                        "'量价确认'、'仓位管理'、'关键支撑/阻力'等投研措辞；"
                        "避免鸡汤式总结和过度绝对化判断。"
                        "只返回JSON对象，不要输出Markdown。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "请输出一个JSON对象，字段必须包含："
                        "market_overview(字符串), technical_analysis(字符串), "
                        "risk_assessment(字符串), trading_signals(字符串数组，3到5条), "
                        "trend_enhanced_analysis(字符串), "
                        "sentiment_deep_analysis(对象，包含 current_interpretation/weekly_trend/"
                        "historical_comparison/market_impact/investor_behavior/trading_advice), "
                        "financial_analyst(对象，包含 overall_points(5条数组)/"
                        "short_term(对象: stance/summary/action_items)/"
                        "long_term(对象: stance/summary/action_items))。"
                        "要求：内容必须基于输入数据，不编造不存在的价格点位；"
                        "technical_analysis 可包含少量HTML片段；"
                        "trading_signals 每条一句中文；"
                        f"输入数据: {json.dumps(prompt_context, ensure_ascii=False)}"
                    ),
                },
            ],
        }

    @staticmethod
    def _extract_deepseek_content(response: Dict[str, Any]) -> str:
        choices = response.get("choices", [])
        if not choices:
            raise ValueError("DeepSeek 返回缺少 choices")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not content:
            raise ValueError("DeepSeek 返回缺少 content")
        return content

    @staticmethod
    def _normalize_ai_output(content: str) -> Dict[str, Any]:
        data = json.loads(AIAnalysisService._extract_json_payload(content))
        required_fields = {
            "market_overview",
            "technical_analysis",
            "risk_assessment",
            "trading_signals",
            "sentiment_deep_analysis",
            "financial_analyst",
        }
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"DeepSeek 返回缺少字段: {', '.join(missing)}")
        if not isinstance(data["trading_signals"], list):
            raise ValueError("DeepSeek trading_signals 不是数组")
        data["trading_signals"] = [
            str(item).strip()
            for item in data["trading_signals"]
            if str(item).strip()
        ][:5]
        if not isinstance(data["sentiment_deep_analysis"], dict):
            raise ValueError("DeepSeek sentiment_deep_analysis 不是对象")
        if not isinstance(data["financial_analyst"], dict):
            raise ValueError("DeepSeek financial_analyst 不是对象")
        return data

    @staticmethod
    def _extract_json_payload(content: str) -> str:
        text = str(content or "").strip()
        if not text:
            raise ValueError("DeepSeek 返回内容为空")

        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fenced_match:
            return fenced_match.group(1)

        if text.startswith("{") and text.endswith("}"):
            return text

        start = text.find("{")
        if start == -1:
            raise ValueError("DeepSeek 返回内容中未找到 JSON 对象")

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        raise ValueError("DeepSeek 返回 JSON 不完整")

    def _generate_deepseek_analysis(
        self,
        fear_greed_index: Dict[str, Any],
        crypto_news: List[Dict[str, Any]],
        market_overview: Dict[str, Any],
        technical_context: Dict[str, Any],
        macro_context: Dict[str, Any],
        defi_overview: Dict[str, Any],
        sentiment_counts: Dict[str, int],
        weekly_ai_trend: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self._has_deepseek_config():
            self.logger.info("未配置 DeepSeek API Key，跳过 AI 分析生成")
            return {}

        try:
            payload = self._build_deepseek_payload(
                fear_greed_index,
                crypto_news,
                market_overview,
                technical_context,
                macro_context,
                defi_overview,
                sentiment_counts,
                weekly_ai_trend,
            )
            response = self.http.post_json(
                self.config.deepseek_api_url,
                payload,
                timeout=self.config.deepseek_request_timeout_seconds,
                headers=self._deepseek_headers(),
            )
            content = self._extract_deepseek_content(response)
            analysis = self._normalize_ai_output(content)
            self.logger.info("DeepSeek 分析生成成功")
            return analysis
        except Exception as exc:
            self.logger.warning("DeepSeek 分析生成失败，回退规则分析: %s", exc)
            return {}

    def analyze_ai_weekly_trend(
        self,
        fear_greed_index: Dict[str, Any],
        market_overview: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            if not fear_greed_index or not market_overview:
                return {
                    "market_trend": "unknown",
                    "volatility_trend": "unknown",
                    "sentiment_trend": "unknown",
                    "key_patterns": ["数据不足，无法进行分析"],
                    "anomalies_detected": [],
                    "confidence_score": 0.0,
                }

            fgi_value = fear_greed_index.get("value", 50)
            market_change = market_overview.get(
                "market_cap_change_percentage_24h_usd",
                0,
            )
            if market_change > 1.0:
                market_trend = "uptrend"
            elif market_change < -1.0:
                market_trend = "downtrend"
            else:
                market_trend = "consolidation"

            weekly_change = fear_greed_index.get("weekly_change")
            if weekly_change is None:
                sentiment_trend = "stable"
                volatility_trend = "stable"
            else:
                if weekly_change > 5:
                    sentiment_trend = "improving"
                elif weekly_change < -5:
                    sentiment_trend = "declining"
                else:
                    sentiment_trend = "stable"

                if abs(weekly_change) >= 12:
                    volatility_trend = "increasing"
                elif abs(weekly_change) <= 3:
                    volatility_trend = "decreasing"
                else:
                    volatility_trend = "stable"

            return {
                "market_trend": market_trend,
                "volatility_trend": volatility_trend,
                "sentiment_trend": sentiment_trend,
                "key_patterns": [
                    f"市场处于{self.get_market_trend_text(market_trend)}，24小时变化{market_change:.2f}%",
                    f"情绪指数{fgi_value}，周度变化{fear_greed_index.get('weekly_change')}",
                    f"月度变化{fear_greed_index.get('monthly_change')}",
                ],
                "anomalies_detected": [],
                "confidence_score": 0.8,
            }
        except Exception as exc:
            self.logger.warning(f"AI周度趋势分析失败: {exc}")
            return {}

    @staticmethod
    def generate_ai_trend_enhanced_analysis(weekly_trend: Dict[str, Any]) -> str:
        if not weekly_trend:
            return "暂无周度AI趋势数据"
        trend_analysis = []
        market_trend = weekly_trend.get("market_trend", "unknown")
        sentiment_trend = weekly_trend.get("sentiment_trend", "stable")
        if market_trend == "uptrend":
            trend_analysis.append("📈 周度市场趋势：上涨趋势，买盘力量增强")
        elif market_trend == "downtrend":
            trend_analysis.append("📉 周度市场趋势：下跌趋势，卖压持续")
        else:
            trend_analysis.append("⚖️ 周度市场趋势：盘整阶段，等待突破方向")

        if sentiment_trend == "improving":
            trend_analysis.append("😊 周度情绪趋势：逐步改善，恐慌情绪缓解")
        elif sentiment_trend == "declining":
            trend_analysis.append("😨 周度情绪趋势：持续恶化，恐慌加剧")
        else:
            trend_analysis.append("😐 周度情绪趋势：保持稳定，无明显变化")

        return "\n".join(trend_analysis)

    @staticmethod
    def get_market_trend_text(market_trend: str) -> str:
        return {
            "uptrend": "上涨趋势",
            "downtrend": "下跌趋势",
            "consolidation": "盘整阶段",
            "unknown": "未知阶段",
        }.get(market_trend, "未知阶段")

    def generate_dynamic_market_overview(
        self,
        fgi_value: int,
        market_data: Dict[str, Any],
        sentiment_counts: Dict[str, int],
        news_focus_summary: str = "",
        weekly_trend: Dict[str, Any] | None = None,
        macro_context: Dict[str, Any] | None = None,
        defi_overview: Dict[str, Any] | None = None,
    ) -> str:
        market_cap_change = market_data.get("market_cap_change_percentage_24h_usd", 0)
        btc_dominance = market_data.get("market_cap_percentage", {}).get("btc", 50)
        sentiment_bucket = self.sentiment_service.get_sentiment_bucket(fgi_value)
        parts = []
        if sentiment_bucket == "extreme_fear":
            parts.append(f"📉 市场情绪极度悲观（{fgi_value}/100），投资者普遍持谨慎态度。")
            parts.append("历史数据显示，当恐惧贪婪指数低于20时，市场往往处于超卖状态。")
        elif sentiment_bucket == "fear":
            parts.append(f"⚠️ 市场情绪偏向恐惧（{fgi_value}/100），投资者观望情绪浓厚。")
        elif sentiment_bucket == "neutral":
            parts.append(f"⚖️ 市场情绪相对平衡（{fgi_value}/100），多空力量较为均衡。")
        elif sentiment_bucket == "greed":
            parts.append(f"📈 市场情绪偏向贪婪（{fgi_value}/100），风险偏好有所回升。")
        else:
            parts.append(f"🚨 市场情绪极度贪婪（{fgi_value}/100），需警惕回调风险。")

        if market_cap_change > 0:
            parts.append(f"总市值24小时上涨{market_cap_change:.2f}%，显示买盘有所恢复。")
        else:
            parts.append(f"总市值24小时下跌{abs(market_cap_change):.2f}%，卖压依然存在。")
        parts.append(f"比特币主导地位为{btc_dominance:.1f}%，显示其避险属性得到市场认可。")

        total_news = sum(sentiment_counts.values())
        if total_news > 0:
            positive_ratio = sentiment_counts["positive"] / total_news * 100
            if positive_ratio > 50:
                parts.append("新闻情绪偏正面，市场关注积极发展。")
            elif positive_ratio < 30:
                parts.append("新闻情绪偏谨慎，市场关注风险因素。")
            else:
                parts.append("新闻情绪相对平衡，多空消息交织。")
        if news_focus_summary:
            parts.append(news_focus_summary)
        macro_summary = self._summarize_macro_context(macro_context or {})
        if macro_summary:
            parts.append(macro_summary)
        defi_summary = self._summarize_defi_context(defi_overview or {})
        if defi_summary:
            parts.append(defi_summary)

        if weekly_trend:
            market_trend = weekly_trend.get("market_trend", "unknown")
            sentiment_trend = weekly_trend.get("sentiment_trend", "stable")
            if market_trend == "uptrend":
                parts.append("从周度趋势看，市场呈现上涨态势，买盘力量逐步增强。")
            elif market_trend == "downtrend":
                parts.append("周度趋势显示市场仍处于下跌通道，卖压持续。")
            else:
                parts.append("周度市场处于盘整阶段，多空力量相对均衡。")
            if sentiment_trend == "improving":
                parts.append("情绪趋势逐步改善，市场恐慌有所缓解。")
            elif sentiment_trend == "declining":
                parts.append("情绪趋势持续恶化，需保持高度警惕。")
        return " ".join(parts)

    @staticmethod
    def generate_dynamic_technical_analysis(
        fgi_value: int,
        technical_context: Dict[str, Any] | None = None,
        weekly_trend: Dict[str, Any] | None = None,
        macro_context: Dict[str, Any] | None = None,
        defi_overview: Dict[str, Any] | None = None,
    ) -> str:
        technical_context = technical_context or {}
        btc_context = technical_context.get("BTC", {})
        eth_context = technical_context.get("ETH", {})
        btc_latest = float(btc_context.get("latest_close", 0) or 0)
        btc_low_30d = float(btc_context.get("low_30d", 0) or 0)
        btc_high_30d = float(btc_context.get("high_30d", 0) or 0)
        btc_support = (
            btc_low_30d
            if btc_low_30d > 0
            else btc_latest * 0.9 if btc_latest > 0 else 40000
        )
        btc_resistance = (
            btc_high_30d
            if btc_high_30d > 0
            else btc_latest * 1.05 if btc_latest > 0 else 45000
        )
        btc_range_text = (
            f"近30天价格区间约为 ${btc_low_30d:,.0f} - ${btc_high_30d:,.0f}"
            if btc_low_30d > 0 and btc_high_30d > 0
            else "需继续观察近30天区间结构"
        )
        btc_summary = AIAnalysisService._build_asset_technical_summary("BTC", btc_context)
        eth_summary = AIAnalysisService._build_asset_technical_summary("ETH", eth_context)
        summary_lines = [line for line in [btc_summary, eth_summary] if line]
        summary_html = ""
        if summary_lines:
            summary_html = (
                '<div style="margin-bottom: 10px; padding: 10px 12px; background: #f8fafc; '
                'border: 1px solid #e7edf4; border-radius: 10px; font-size: 0.9em; color: #475569;">'
                + " ".join(summary_lines)
                + "</div>"
            )
        if fgi_value <= 20:
            analysis = f"""
            <div class="technical-analysis">
                <ul>
                    <li><strong>超卖状态明显</strong>：多数主流币RSI指标低于30，显示技术性超卖</li>
                    <li><strong>关键支撑测试</strong>：比特币正围绕 ${btc_support:,.0f} 一带寻找支撑，需观察是否形成止跌结构</li>
                    <li><strong>成交量萎缩</strong>：市场交投清淡，观望情绪浓厚</li>
                    <li><strong>区间观察</strong>：{btc_range_text}</li>
                </ul>
            </div>
            """
        elif fgi_value <= 40:
            analysis = f"""
            <div class="technical-analysis">
                <ul>
                    <li><strong>震荡整理</strong>：主要币种在关键支撑阻力区间内震荡</li>
                    <li><strong>均线压制</strong>：价格受短期均线压制，需要放量突破</li>
                    <li><strong>支撑测试</strong>：关注 ${btc_support:,.0f} 一带支撑是否有效</li>
                    <li><strong>指标修复</strong>：RSI指标从超卖区域有所修复</li>
                </ul>
            </div>
            """
        else:
            analysis = f"""
            <div class="technical-analysis">
                <ul>
                    <li><strong>趋势分化</strong>：各币种走势出现分化，需区别对待</li>
                    <li><strong>关键阻力</strong>：关注 ${btc_resistance:,.0f} 一带能否有效突破</li>
                    <li><strong>成交量配合</strong>：上涨需要成交量放大配合</li>
                    <li><strong>指标健康</strong>：主要技术指标处于健康区间</li>
                </ul>
            </div>
            """

        if weekly_trend:
            volatility_trend = weekly_trend.get("volatility_trend", "stable")
            patterns = weekly_trend.get("key_patterns", [])
            analysis = analysis.replace(
                "</ul>",
                (
                    "<li><strong>周度波动趋势</strong>："
                    f"{AIAnalysisService.get_volatility_trend_text(volatility_trend)}</li></ul>"
                ),
            )
            if patterns:
                analysis += (
                    '<div style="margin-top: 10px; padding: 10px; background: #f8f9fa; '
                    'border-radius: 5px; font-size: 0.9em;">'
                    f'<strong>🔍 周度技术观察：</strong> {patterns[0]}</div>'
                )
        macro_context = macro_context or {}
        strongest_macro = (macro_context.get("assets") or [{}])[0]
        if strongest_macro.get("label") and strongest_macro.get("correlation_30d") is not None:
            analysis += (
                '<div style="margin-top: 10px; padding: 10px; background: #f8f9fa; '
                'border-radius: 5px; font-size: 0.9em;">'
                f"<strong>🌐 宏观联动：</strong> BTC 与{strongest_macro['label']}近30天相关性为"
                f" {float(strongest_macro['correlation_30d']):+.2f}，需关注外部市场共振风险。</div>"
            )
        defi_overview = defi_overview or {}
        top_protocols = defi_overview.get("top_protocols") or []
        if top_protocols:
            protocol = top_protocols[0]
            analysis += (
                '<div style="margin-top: 10px; padding: 10px; background: #f8f9fa; '
                'border-radius: 5px; font-size: 0.9em;">'
                f"<strong>🏦 DeFi 观察：</strong> {protocol.get('name', '头部协议')} 维持较高 TVL，"
                f"说明链上流动性尚未明显衰竭。</div>"
            )
        return summary_html + analysis

    @staticmethod
    def _build_asset_technical_summary(symbol: str, context: Dict[str, Any]) -> str:
        if not context:
            return ""
        ma7 = context.get("ma7")
        ma30 = context.get("ma30")
        rsi14 = context.get("rsi14")
        bollinger_status = str(context.get("bollinger_status", "") or "")
        parts = []
        if ma7 is not None and ma30 is not None:
            parts.append("短期强于中期均线" if float(ma7) >= float(ma30) else "短期仍弱于中期均线")
        if rsi14 is not None:
            rsi_value = float(rsi14)
            if rsi_value < 30:
                parts.append("RSI 接近超卖")
            elif rsi_value > 70:
                parts.append("RSI 偏强但需防过热")
            else:
                parts.append("RSI 处于中性区间")
        if bollinger_status:
            parts.append(f"布林带显示{bollinger_status}")
        if not parts:
            return ""
        return f"<strong>{symbol}</strong>：" + "，".join(parts) + "。"

    @staticmethod
    def get_volatility_trend_text(volatility_trend: str) -> str:
        return {
            "decreasing": "波动率下降，市场趋于稳定",
            "increasing": "波动率上升，市场不确定性增加",
            "stable": "波动率稳定，市场正常波动",
        }.get(volatility_trend, "波动趋势未知")

    @staticmethod
    def get_financial_technical_trend_text(weekly_trend: Dict[str, Any]) -> str:
        if not weekly_trend:
            return ""
        market_trend = weekly_trend.get("market_trend", "unknown")
        volatility_trend = weekly_trend.get("volatility_trend", "stable")
        if market_trend == "uptrend":
            trend_text = "周度技术面呈现上涨态势，"
        elif market_trend == "downtrend":
            trend_text = "周度技术面仍处于下跌通道，"
        else:
            trend_text = "周度技术面处于盘整阶段，"
        if volatility_trend == "decreasing":
            return trend_text + "波动率下降显示市场趋于稳定。"
        if volatility_trend == "increasing":
            return trend_text + "波动率上升增加市场不确定性。"
        return trend_text + "波动率保持稳定。"

    def generate_dynamic_risk_assessment(
        self,
        fgi_value: int,
        sentiment_counts: Dict[str, int],
        macro_context: Dict[str, Any] | None = None,
        defi_overview: Dict[str, Any] | None = None,
    ) -> str:
        negative_news = sentiment_counts.get("negative", 0)
        total_news = sum(sentiment_counts.values())
        sentiment_bucket = self.sentiment_service.get_sentiment_bucket(fgi_value)
        sentiment_profile = self.sentiment_service.get_sentiment_profile(fgi_value)
        risk_text = (
            sentiment_profile["risk_assessment_light"]
            if sentiment_bucket == "extreme_fear" and negative_news <= total_news * 0.5
            else sentiment_profile["risk_assessment"]
        )
        macro_context = macro_context or {}
        if any(abs(float(item.get("correlation_30d", 0.0))) >= 0.5 for item in (macro_context.get("assets") or [])):
            risk_text += " 当前 BTC 与外部风险资产联动增强，需防范宏观市场波动传导。"
        defi_overview = defi_overview or {}
        if not (defi_overview.get("top_protocols") or []):
            risk_text += " 链上流动性样本有限，DeFi 风险评估需保持保守。"
        return risk_text

    def generate_dynamic_trading_signals(
        self,
        fgi_value: int,
        news_keywords: List[str],
        macro_context: Dict[str, Any] | None = None,
        defi_overview: Dict[str, Any] | None = None,
    ) -> List[str]:
        sentiment_profile = self.sentiment_service.get_sentiment_profile(fgi_value)
        signals = list(sentiment_profile.get("base_signals", []))
        if "比特币" in news_keywords:
            signals.append("关注比特币：作为市场风向标，比特币走势至关重要")
        if "监管" in news_keywords:
            signals.append("政策敏感：监管消息可能引发市场波动，需密切关注")
        if "技术" in news_keywords:
            signals.append("技术驱动：技术进展可能带来结构性机会")
        macro_context = macro_context or {}
        assets = macro_context.get("assets") or []
        if assets:
            dominant_link = max(assets, key=lambda item: abs(float(item.get("correlation_30d", 0.0))))
            signals.append(
                f"关注宏观联动：BTC 与{dominant_link.get('label', '外部市场')}相关性较高，注意外盘风险传导"
            )
        defi_overview = defi_overview or {}
        protocols = defi_overview.get("top_protocols") or []
        if protocols:
            signals.append(
                f"链上资金观察：关注 {protocols[0].get('name', '头部协议')} TVL 变化，判断风险偏好是否延续"
            )
        return signals[:5]

    def build_sentiment_deep_analysis(
        self,
        sentiment_analysis: Dict[str, Any],
        market_overview: Dict[str, Any],
    ) -> Dict[str, str]:
        market_change = market_overview.get("market_cap_change_percentage_24h_usd", 0)
        if market_change >= 2:
            market_impact = "总市值短线回暖，说明风险偏好有所恢复，但持续性仍需成交量确认。"
        elif market_change <= -2:
            market_impact = "总市值继续承压，市场仍处于防御模式，情绪修复尚未完成。"
        else:
            market_impact = "总市值波动有限，市场仍以试探和等待方向选择为主。"

        return {
            "current_interpretation": str(
                sentiment_analysis.get("description", "当前市场情绪暂无明确结论")
            ),
            "weekly_trend": str(
                sentiment_analysis.get("trend_analysis", "暂无周度趋势数据")
            ),
            "historical_comparison": self._build_historical_comparison_text(
                sentiment_analysis,
            ),
            "market_impact": market_impact,
            "investor_behavior": str(
                self.sentiment_service.get_sentiment_profile(
                    sentiment_analysis.get("value", 50)
                ).get("investor_behavior", "")
            ),
            "trading_advice": str(
                sentiment_analysis.get("recommendation", "建议继续观察市场变化")
            ),
        }

    @staticmethod
    def _build_historical_comparison_text(sentiment_analysis: Dict[str, Any]) -> str:
        historical_data = sentiment_analysis.get("historical_data") or []
        current_value = sentiment_analysis.get("value", 0)
        if not historical_data:
            return "暂无足够历史数据进行比较"
        values = [
            int(item.get("value"))
            for item in historical_data[:30]
            if item.get("value") is not None
        ]
        if not values:
            return "暂无足够历史数据进行比较"
        average = sum(values) / len(values)
        diff = current_value - average
        if diff >= 10:
            return f"当前指数显著高于近30天均值（{average:.1f}），情绪修复力度较强。"
        if diff >= 3:
            return f"当前指数略高于近30天均值（{average:.1f}），情绪边际改善。"
        if diff <= -10:
            return f"当前指数显著低于近30天均值（{average:.1f}），市场仍处于深度谨慎阶段。"
        if diff <= -3:
            return f"当前指数低于近30天均值（{average:.1f}），资金偏防御。"
        return f"当前指数接近近30天均值（{average:.1f}），市场情绪处于常态区间。"

    def build_financial_analyst_view(
        self,
        sentiment_analysis: Dict[str, Any],
        market_overview: Dict[str, Any],
        sentiment_counts: Dict[str, int],
        news_tag_summary: Dict[str, int],
        weekly_ai_trend: Dict[str, Any],
        macro_context: Dict[str, Any] | None = None,
        defi_overview: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        value = sentiment_analysis.get("value", 50)
        classification = sentiment_analysis.get("classification", "中性")
        market_change = market_overview.get("market_cap_change_percentage_24h_usd", 0)
        btc_dominance = market_overview.get("market_cap_percentage", {}).get("btc", 0)
        positive = sentiment_counts.get("positive", 0)
        negative = sentiment_counts.get("negative", 0)
        news_focus_summary = self.summarize_news_focus(news_tag_summary)
        overall_points = [
            f"市场情绪当前为{classification}（{value}分），情绪仍是短线定价的重要变量。",
            f"总市值24小时变化为{market_change:+.2f}%，说明风险偏好{'回暖' if market_change > 0 else '仍偏弱' if market_change < 0 else '暂未形成方向'}。",
            f"比特币市值占比为{btc_dominance:.1f}%，反映资金在主流资产与避险偏好之间的平衡。",
            f"新闻面统计显示正面{positive}条、负面{negative}条，消息面对盘面形成{'一定支撑' if positive >= negative else '一定压制'}。",
            news_focus_summary,
            (
                f"结合趋势观察，当前更适合{'等待确认后逐步提高风险暴露' if value > 40 else '控制仓位并耐心等待情绪修复'}。"
                f"{self._summarize_weekly_trend(weekly_ai_trend)}"
            ),
        ]
        macro_summary = self._summarize_macro_context(macro_context or {})
        if macro_summary:
            overall_points.append(macro_summary)
        defi_summary = self._summarize_defi_context(defi_overview or {})
        if defi_summary:
            overall_points.append(defi_summary)

        short_term_stance = "谨慎" if value <= 40 else "中性偏谨慎" if value <= 60 else "中性偏积极"
        long_term_stance = "潜在机会" if value <= 40 else "中性布局"

        return {
            "overall_points": overall_points,
            "short_term": {
                "stance": short_term_stance,
                "summary": (
                    "短线更适合围绕情绪修复节奏和关键支撑阻力做仓位管理，"
                    "避免在缺乏量能确认时激进追价。"
                ),
                "action_items": [
                    "保持分批进出，避免一次性重仓决策",
                    "优先观察比特币和以太坊关键支撑是否有效",
                    "若市场继续缩量，降低交易频率，等待明确方向",
                    "出现反弹时先看量价配合，再决定是否扩大仓位",
                    "严格执行止损和回撤控制，避免情绪化交易",
                ],
            },
            "long_term": {
                "stance": long_term_stance,
                "summary": (
                    "长期仍应关注行业基本面、监管演进和主流资产资金流向，"
                    "在情绪极端阶段保留逆向布局的耐心。"
                ),
                "action_items": [
                    "采用定投或分批建仓方式平滑波动",
                    "优先配置流动性较好、基本面更强的主流资产",
                    "持续跟踪监管、ETF资金流和链上活跃度变化",
                    "对高波动小币种保持更高的仓位纪律",
                    "将组合收益目标建立在中周期而非单日波动上",
                ],
            },
        }

    @staticmethod
    def _summarize_macro_context(macro_context: Dict[str, Any]) -> str:
        assets = macro_context.get("assets") or []
        if not assets:
            return ""
        strongest = max(
            assets,
            key=lambda item: abs(float(item.get("correlation_30d", 0.0))),
        )
        correlation = float(strongest.get("correlation_30d", 0.0))
        if abs(correlation) >= 0.5:
            return (
                f"宏观层面，BTC 与{strongest.get('label', '外部市场')}的30天相关性达到"
                f"{correlation:+.2f}，短线需关注传统市场波动外溢。"
            )
        return (
            f"宏观层面，BTC 与{strongest.get('label', '外部市场')}的30天相关性为"
            f"{correlation:+.2f}，当前联动性仍处可控区间。"
        )

    @staticmethod
    def _summarize_defi_context(defi_overview: Dict[str, Any]) -> str:
        top_chains = defi_overview.get("top_chains") or []
        top_protocols = defi_overview.get("top_protocols") or []
        if not top_chains and not top_protocols:
            return ""
        chain_part = ""
        if top_chains:
            chain_part = (
                f"DeFi 资金仍主要集中在{top_chains[0].get('name', '头部链')}，"
                f"占比约 {float(top_chains[0].get('share_pct', 0.0)):.1f}%"
            )
        protocol_part = ""
        if top_protocols:
            protocol_part = (
                f"，头部协议 {top_protocols[0].get('name', 'Unknown')} 维持较高 TVL"
            )
        return chain_part + protocol_part + "。"

    @staticmethod
    def _summarize_weekly_trend(weekly_ai_trend: Dict[str, Any]) -> str:
        if not weekly_ai_trend:
            return ""
        market_trend = weekly_ai_trend.get("market_trend", "unknown")
        sentiment_trend = weekly_ai_trend.get("sentiment_trend", "stable")
        market_text = {
            "uptrend": "周度市场保持上行结构，",
            "downtrend": "周度市场仍处下行通道，",
            "consolidation": "周度市场仍以盘整为主，",
        }.get(market_trend, "")
        sentiment_text = {
            "improving": "情绪边际改善。",
            "declining": "情绪继续走弱。",
            "stable": "情绪暂无明显修复信号。",
        }.get(sentiment_trend, "")
        return market_text + sentiment_text
