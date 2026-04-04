"""Core report generation pipeline."""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from .config import ScriptConfig, load_script_config
from .helpers import build_change_meta, get_sentiment_color, get_structured_weekly_trend
from .http_client import HTTPClient
from .logging_utils import configure_logging, get_logger
from .models import FearGreedIndex, MarketOverview, NewsItem, ReportContext
from .renderers import (
    generate_ai_analysis_section,
    generate_crypto_table_rows,
    generate_financial_analyst_section,
    generate_technical_context_section,
    generate_top_focus_assets_section,
    generate_market_pulse_section,
    generate_market_overview_section,
    generate_news_html,
    generate_sentiment_analysis_section,
    generate_trading_signals_html,
)
from .services import (
    AIAnalysisService,
    MarketService,
    NewsService,
    SentimentService,
    TrendStorage,
)

APP_CONFIG = load_script_config()
configure_logging(APP_CONFIG)
logger = get_logger(__name__)


class CryptoReportGenerator:
    """Coordinates data fetching, analysis, rendering, and output."""

    def __init__(
        self,
        config: Optional[ScriptConfig] = None,
        report_date: Optional[dt] = None,
    ):
        self.config = config or APP_CONFIG
        self.report_date = report_date or dt.now()
        self.report_dir = str(self.config.report_dir)
        self.trend_data_file = self.config.trend_data_file
        self.report_base_url = self.config.normalized_report_base_url
        self.report_stylesheet_name = self.config.report_stylesheet_filename
        self.http = HTTPClient(self.config, logger)
        self.template_env = self._build_template_environment()
        self.version = self.config.report_version
        self.last_updated = "2026-04-03"

        self.storage = TrendStorage(self.trend_data_file, self.report_date, logger)
        self.market_service = MarketService(
            self.config,
            self.http,
            logger,
            self.report_date,
            self.storage,
        )
        self.news_service = NewsService(self.config, self.http, logger)
        self.sentiment_service = SentimentService(logger)
        self.analysis_service = AIAnalysisService(
            self.config,
            self.http,
            logger,
            self.sentiment_service,
        )

        self.market_overview: MarketOverview = {}
        self.fear_greed_index: FearGreedIndex = {}
        self.crypto_news: List[NewsItem] = []
        self.top_cryptos: List[Dict[str, Any]] = []
        self.market_cap_history: List[Dict[str, Any]] = []
        self.technical_context: Dict[str, Any] = {}
        self.sentiment: FearGreedIndex = {}
        self.news_date_range = self.news_service.news_date_range

        os.makedirs(self.report_dir, exist_ok=True)
        self.trend_data_file.parent.mkdir(parents=True, exist_ok=True)
        self._log_config_warnings()

    def _build_template_environment(self):
        if Environment is None or FileSystemLoader is None or select_autoescape is None:
            return None
        return Environment(
            loader=FileSystemLoader(str(self.config.report_template_file.parent)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _log_config_warnings(self) -> None:
        if self.config.ignores_asset_url_mode():
            logger.info(
                "report_css_mode=inline 时将忽略 report_asset_url_mode=%s",
                self.config.report_asset_url_mode,
            )

    def _collect_core_data(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "fear_greed_index": executor.submit(self.get_fear_greed_index),
                "crypto_news": executor.submit(self.get_crypto_news),
                "market_overview": executor.submit(self.get_market_overview),
                "top_cryptos": executor.submit(self.get_top_cryptocurrencies, 10),
                "market_cap_history": executor.submit(self.get_market_cap_history, 30),
                "technical_context": executor.submit(self.get_technical_context),
            }
            self.fear_greed_index = futures["fear_greed_index"].result()
            self.crypto_news = futures["crypto_news"].result()
            self.market_overview = futures["market_overview"].result()
            self.top_cryptos = futures["top_cryptos"].result()
            self.market_cap_history = futures["market_cap_history"].result()
            self.technical_context = futures["technical_context"].result()
            self.news_date_range = self.news_service.news_date_range

    def _build_report_context(self) -> ReportContext:
        sentiment = self.sentiment
        return {
            "report_time": self.report_date.strftime("%Y-%m-%d %H:%M"),
            "market_overview": self.market_overview,
            "top_cryptos": self.top_cryptos or self.get_top_cryptocurrencies(10),
            "top_focus_assets": (self.top_cryptos or self.get_top_cryptocurrencies(10))[:5],
            "market_cap_history": self.market_cap_history or self.get_market_cap_history(30),
            "technical_context": self.technical_context or self.get_technical_context(),
            "news": self.crypto_news,
            "sentiment": sentiment,
            "daily_change_meta": build_change_meta(sentiment.get("daily_change")),
            "weekly_change_meta": build_change_meta(sentiment.get("weekly_change")),
            "monthly_change_meta": build_change_meta(sentiment.get("monthly_change")),
            "weekly_trend": get_structured_weekly_trend(sentiment),
            "dynamic_analysis": self.get_dynamic_analysis(sentiment.get("value", 50)),
            "ai_analysis": self.get_ai_analysis(),
        }

    def get_market_overview(self) -> MarketOverview:
        return self.market_service.get_market_overview()

    def get_top_cryptocurrencies(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.market_service.get_top_cryptocurrencies(limit)

    def get_fear_greed_index(self, limit: int = 7) -> FearGreedIndex:
        return self.market_service.get_fear_greed_index(limit)

    def get_market_cap_history(self, days: int = 30) -> List[Dict[str, Any]]:
        return self.market_service.get_market_cap_history(days)

    def get_technical_context(self) -> Dict[str, Any]:
        return self.market_service.get_technical_context()

    def _load_trend_data(self) -> Dict[str, Any]:
        return self.storage.load()

    def _save_trend_data(self, data: Dict[str, Any]) -> bool:
        return self.storage.save(data)

    def _update_fear_greed_trend(self, current_value: int, classification: str) -> Dict[str, Any]:
        return self.storage.update_fear_greed_trend(current_value, classification)

    def _update_market_data_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.storage.update_market_data_trend(market_data)

    def _update_price_trend(self, symbol: str, price: float, change_24h: float) -> Dict[str, Any]:
        return self.storage.update_price_trend(symbol, price, change_24h)

    def _calculate_weekly_change_from_trend(self, current_value: int) -> Optional[int]:
        return self.storage.calculate_weekly_change_from_trend(current_value)

    def _calculate_30day_average_from_trend(
        self,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[float]:
        return self.storage.calculate_30day_average_from_trend(
            historical_data=historical_data,
        )

    def _generate_historical_comparison(
        self,
        current_value: int,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        return self.storage.generate_historical_comparison(
            current_value,
            historical_data=historical_data,
        )

    def get_yesterday_sentiment(self) -> Dict[str, Any]:
        return self.storage.get_yesterday_sentiment()

    def get_crypto_news(self) -> List[NewsItem]:
        news = self.news_service.get_crypto_news()
        self.news_date_range = self.news_service.news_date_range
        return news

    def _get_backup_news(self) -> List[NewsItem]:
        return self.news_service.get_backup_news()

    def _get_sentiment_bucket(self, value: int) -> str:
        return self.sentiment_service.get_sentiment_bucket(value)

    def _get_sentiment_profile(self, value: int) -> Dict[str, Any]:
        return self.sentiment_service.get_sentiment_profile(value)

    def _generate_ai_analysis_section(self, ai_analysis: Dict[str, Any]) -> str:
        trading_signals_html = self._generate_trading_signals_html(
            ai_analysis.get("trading_signals", [])
        )
        return generate_ai_analysis_section(ai_analysis, trading_signals_html)

    def _generate_sentiment_analysis_section(
        self,
        sentiment: Dict[str, Any],
        report_time: str,
        daily_change_str: str,
        weekly_change_str: str,
        monthly_change_str: str,
        daily_change_class: str,
        weekly_change_class: str,
        monthly_change_class: str,
        deep_analysis: Dict[str, str],
    ) -> str:
        sentiment_value = int(sentiment.get("value", 0))
        return generate_sentiment_analysis_section(
            sentiment=sentiment,
            report_time=report_time,
            daily_change_str=daily_change_str,
            weekly_change_str=weekly_change_str,
            monthly_change_str=monthly_change_str,
            daily_change_class=daily_change_class,
            weekly_change_class=weekly_change_class,
            monthly_change_class=monthly_change_class,
            sentiment_bar_color=get_sentiment_color(sentiment_value),
            sentiment_updated_at=report_time,
            deep_analysis=deep_analysis,
        )

    def _sync_report_assets(self):
        if self.config.should_inline_css():
            return
        target_stylesheet = Path(self.report_dir) / self.report_stylesheet_name
        if self.config.report_stylesheet_file.exists():
            shutil.copy2(self.config.report_stylesheet_file, target_stylesheet)

    def _load_inline_styles(self) -> str:
        if not self.config.should_inline_css():
            return ""
        return self.config.report_stylesheet_file.read_text(encoding="utf-8")

    def get_sentiment_analysis(self) -> FearGreedIndex:
        return self.sentiment_service.get_sentiment_analysis(self.fear_greed_index)

    def _analyze_sentiment_weekly_trend(self, fgi_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.sentiment_service.analyze_sentiment_weekly_trend(fgi_data)

    def _generate_sentiment_trend_analysis(self, current_value: int, weekly_trend: Dict[str, Any]) -> str:
        return self.sentiment_service.generate_sentiment_trend_analysis(current_value, weekly_trend)

    def _get_sentiment_recommendation(self, value: int, weekly_trend: Dict[str, Any] | None = None) -> str:
        return self.sentiment_service.get_sentiment_recommendation(value, weekly_trend)

    def _get_volatility_text(self, volatility: str) -> str:
        return self.sentiment_service.get_volatility_text(volatility)

    def get_ai_analysis(self) -> Dict[str, Any]:
        fear_greed_index = self.fear_greed_index or self.sentiment or {
            "value": 50,
            "classification": "中性",
        }
        return self.analysis_service.get_ai_analysis(
            fear_greed_index,
            self.crypto_news,
            self.market_overview,
            self.technical_context,
        )

    def _analyze_ai_weekly_trend(self) -> Dict[str, Any]:
        return self.analysis_service.analyze_ai_weekly_trend(
            self.fear_greed_index,
            self.market_overview,
        )

    def _generate_ai_trend_enhanced_analysis(self, current_analysis: Dict[str, Any], weekly_trend: Dict[str, Any]) -> str:
        del current_analysis
        return self.analysis_service.generate_ai_trend_enhanced_analysis(weekly_trend)

    def _get_financial_sentiment_trend_text(self, weekly_trend: Dict[str, Any]) -> str:
        return self.sentiment_service.get_financial_sentiment_trend_text(weekly_trend)

    def _get_financial_technical_trend_text(self, weekly_trend: Dict[str, Any]) -> str:
        return self.analysis_service.get_financial_technical_trend_text(weekly_trend)

    def _generate_dynamic_risk_assessment(self, fgi_value: int, sentiment_counts: Dict[str, int]) -> str:
        return self.analysis_service.generate_dynamic_risk_assessment(fgi_value, sentiment_counts)

    def _generate_dynamic_trading_signals(self, fgi_value: int, news_keywords: List[str]) -> List[str]:
        return self.analysis_service.generate_dynamic_trading_signals(fgi_value, news_keywords)

    def _generate_trading_signals_html(self, signals: List[str]) -> str:
        return generate_trading_signals_html(signals)

    def get_dynamic_analysis(self, sentiment_value: int) -> Dict[str, str]:
        sentiment_profile = self._get_sentiment_profile(sentiment_value)
        return {
            "market_impact": sentiment_profile["market_impact"],
            "investor_behavior": sentiment_profile["investor_behavior"],
            "risk_level": sentiment_profile["risk_level"],
        }

    def _build_report_public_url(self, filename: str = "") -> str:
        if not filename:
            return self.report_base_url
        return f"{self.report_base_url}{filename.lstrip('/')}"

    def _extract_report_date_from_filename(self, filename: str) -> dt:
        if len(filename) < 10:
            raise ValueError("文件名长度不足，无法解析日期")
        if filename.startswith("modern_"):
            date_str = filename[7:17]
        elif filename.startswith("old_"):
            date_str = filename[4:14]
        else:
            date_str = filename[:10]
        if len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
            raise ValueError("日期格式不正确")
        return dt.strptime(date_str, "%Y-%m-%d")

    def generate_html_report(self) -> str:
        if self.template_env is None:
            raise RuntimeError("缺少 Jinja2 依赖，请先安装 requirements.txt 中的依赖")

        context = self._build_report_context()
        daily_change_meta = context["daily_change_meta"]
        weekly_change_meta = context["weekly_change_meta"]
        monthly_change_meta = context["monthly_change_meta"]
        dynamic_analysis = context["dynamic_analysis"]
        ai_analysis = context["ai_analysis"]
        sentiment = context["sentiment"]
        template = self.template_env.get_template(self.config.report_template_filename)
        return template.render(
            report_title=self.config.report_title,
            report_date_iso=self.report_date.strftime("%Y-%m-%d"),
            report_generated_at=self.report_date.strftime("%Y年%m月%d日 %H:%M:%S"),
            report_generated_at_compact=self.report_date.strftime("%Y-%m-%d %H:%M:%S"),
            report_version=self.version,
            report_system_name=self.config.report_system_name,
            report_base_url=self.report_base_url,
            inline_styles=self._load_inline_styles(),
            stylesheet_href=self.config.build_asset_href(self.report_stylesheet_name),
            market_overview_section=generate_market_overview_section(context["market_overview"]),
            top_focus_assets_section=generate_top_focus_assets_section(context["top_focus_assets"]),
            market_pulse_section=generate_market_pulse_section(
                context["market_overview"],
                context["market_cap_history"],
            ),
            technical_context_section=generate_technical_context_section(
                context["technical_context"]
            ),
            crypto_table_rows=generate_crypto_table_rows(context["top_cryptos"]),
            news_html=generate_news_html(context["news"]),
            news_date_range=self.news_date_range,
            sentiment_section=self._generate_sentiment_analysis_section(
                sentiment=sentiment,
                report_time=context["report_time"],
                daily_change_str=daily_change_meta["text"],
                weekly_change_str=weekly_change_meta["text"],
                monthly_change_str=monthly_change_meta["text"],
                daily_change_class=daily_change_meta["css_class"],
                weekly_change_class=weekly_change_meta["css_class"],
                monthly_change_class=monthly_change_meta["css_class"],
                deep_analysis=ai_analysis.get("sentiment_deep_analysis", {
                    "market_impact": dynamic_analysis["market_impact"],
                    "investor_behavior": dynamic_analysis["investor_behavior"],
                    "historical_comparison": self._generate_historical_comparison(
                        sentiment.get("value", 0),
                        sentiment.get("historical_data"),
                    ),
                    "current_interpretation": sentiment.get("description", ""),
                    "weekly_trend": sentiment.get("trend_analysis", ""),
                    "trading_advice": sentiment.get("recommendation", ""),
                }),
            ),
            ai_analysis_section=self._generate_ai_analysis_section(ai_analysis),
            financial_analyst_section=generate_financial_analyst_section(
                ai_analysis.get("financial_analyst", {})
            ),
            sentiment_value=sentiment["value"],
            sentiment_classification=sentiment["classification"],
            financial_sentiment_trend_text=self._get_financial_sentiment_trend_text(sentiment.get("weekly_trend")),
            financial_technical_trend_text=self._get_financial_technical_trend_text(ai_analysis.get("weekly_trend")),
        )

    def save_report(self):
        try:
            os.makedirs(self.report_dir, exist_ok=True)
            self._sync_report_assets()
            html_content = self.generate_html_report()
            filename = self.config.build_report_filename(self.report_date)
            filepath = os.path.join(self.report_dir, filename)
            with open(filepath, "w", encoding="utf-8") as handle:
                handle.write(html_content)
            latest_path = os.path.join(self.report_dir, self.config.latest_report_filename)
            with open(latest_path, "w", encoding="utf-8") as handle:
                handle.write(html_content)
            logger.info(f"报告已保存: {filepath}")
            logger.info(f"最新报告已更新: {latest_path}")

            if self.config.generate_screenshots:
                screenshot_path = self.generate_screenshot(filepath)
                if screenshot_path and os.path.exists(latest_path):
                    self.generate_screenshot(latest_path)

            self.cleanup_old_reports(self.config.cleanup_days_to_keep)
            return filepath
        except Exception as exc:
            logger.exception(f"保存报告失败: {exc}")
            return None

    def cleanup_old_reports(self, days_to_keep: int = 30):
        try:
            import glob

            cutoff_date = dt.now() - datetime.timedelta(days=days_to_keep)
            logger.info(f"清理 {days_to_keep} 天前的报告，截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
            html_files = glob.glob(os.path.join(self.report_dir, "*.html"))
            png_files = glob.glob(os.path.join(self.report_dir, "*.png"))
            deleted_count = 0
            kept_count = 0

            for filepath in html_files:
                filename = os.path.basename(filepath)
                if filename in [self.config.latest_report_filename, "modern_latest.html"]:
                    kept_count += 1
                    continue
                try:
                    file_date = self._extract_report_date_from_filename(filename)
                    if file_date < cutoff_date:
                        os.remove(filepath)
                        deleted_count += 1
                        png_file = filepath.replace(".html", ".png")
                        if os.path.exists(png_file):
                            os.remove(png_file)
                            deleted_count += 1
                    else:
                        kept_count += 1
                except (ValueError, IndexError):
                    logger.warning(f"跳过无法解析的文件: {filename}")
                    kept_count += 1

            for filepath in png_files:
                filename = os.path.basename(filepath)
                latest_png_name = self.config.latest_report_filename.replace(".html", ".png")
                if filename in [latest_png_name, "modern_latest.png"]:
                    continue
                try:
                    if self._extract_report_date_from_filename(filename) < cutoff_date:
                        os.remove(filepath)
                        deleted_count += 1
                except (ValueError, IndexError):
                    logger.warning(f"跳过无法解析的截图: {filename}")

            logger.info(f"清理完成: 删除 {deleted_count} 个文件，保留 {kept_count} 个文件")
            print(f"🗑️  已清理 {deleted_count} 个 {days_to_keep} 天前的旧报告和截图")
        except Exception as exc:
            logger.exception(f"清理旧报告失败: {exc}")
            print(f"⚠️  清理旧报告时出错: {exc}")

    def generate_screenshot(self, html_path: str):
        try:
            screenshot_path = html_path.replace(".html", ".png")
            if not self.config.generate_screenshots:
                return None
            if self.config.screenshot_backend in ("auto", "wkhtmltoimage"):
                result = subprocess.run(["which", "wkhtmltoimage"], capture_output=True, text=True)
                if result.returncode == 0:
                    cmd = [
                        "wkhtmltoimage",
                        "--quality",
                        "90",
                        "--width",
                        str(self.config.screenshot_width),
                        "--height",
                        "0",
                        "--disable-smart-width",
                        html_path,
                        screenshot_path,
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.config.screenshot_timeout_seconds,
                    )
                    if result.returncode == 0 and os.path.exists(screenshot_path):
                        if os.path.getsize(screenshot_path) / 1024 > 10:
                            logger.info(f"wkhtmltoimage截图生成成功: {screenshot_path}")
                            return screenshot_path
                        os.remove(screenshot_path)
            if self.config.screenshot_backend in ("auto", "playwright"):
                return self.generate_screenshot_playwright(html_path, screenshot_path)
            logger.warning(
                "未找到可用截图后端，请安装 wkhtmltoimage 或执行 `.venv/bin/python -m playwright install chromium`"
            )
            return None
        except Exception as exc:
            logger.warning(f"生成截图时出错: {exc}")
            return None

    def generate_screenshot_playwright(self, html_path: str, screenshot_path: str):
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-setuid-sandbox"],
                    )
                except Exception as exc:
                    logger.warning("playwright 默认 Chromium 启动失败，尝试系统 Chrome: %s", exc)
                    browser = playwright.chromium.launch(
                        channel="chrome",
                        headless=True,
                        args=["--no-sandbox", "--disable-setuid-sandbox"],
                    )
                try:
                    page = browser.new_page()
                    page.set_viewport_size({"width": self.config.screenshot_width, "height": 1000})
                    page.goto(Path(html_path).resolve().as_uri(), wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    height = page.evaluate("() => document.body.scrollHeight")
                    page.set_viewport_size({"width": self.config.screenshot_width, "height": height})
                    page.screenshot(path=screenshot_path, full_page=True, type="png")
                    if os.path.exists(screenshot_path):
                        logger.info(f"playwright截图生成成功: {screenshot_path}")
                        return screenshot_path
                    return None
                finally:
                    browser.close()
        except ImportError:
            logger.warning("playwright未安装，无法生成截图；请先安装 requirements 并执行 playwright install chromium")
            return None
        except Exception as exc:
            logger.warning(f"playwright生成截图失败: {exc}")
            return None

    def run(self):
        logger.info("开始生成数字货币每日分析报告...")
        try:
            self._collect_core_data()
            self.sentiment = self.get_sentiment_analysis()
            report_path = self.save_report()
            if report_path:
                print(f"\n✅ 报告已生成并保存到: {report_path}")
                print(f"🌐 可通过以下地址访问: {self._build_report_public_url()}")
                print(
                    "📅 报告日期: "
                    f"{self.report_date.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)"
                )
                print(f"📊 系统名称: {self.config.report_system_name}")
                print(f"🌐 市场概览来源: {self.market_service.last_market_overview_source}")
                print(f"🪙 币种列表来源: {self.market_service.last_top_cryptos_source}")
                print(f"📰 新闻来源: {self.news_service.last_source_used}")
                screenshot_path = report_path.replace(".html", ".png")
                if os.path.exists(screenshot_path):
                    print(f"🖼️  截图已生成: {screenshot_path}")
                return report_path
            print("❌ 报告生成失败")
            return None
        except Exception as exc:
            logger.exception(f"运行报告生成失败: {exc}")
            print(f"❌ 运行失败: {exc}")
            return None


CryptoAnalystEnhanced = CryptoReportGenerator
