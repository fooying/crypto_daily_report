from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_NEWS_URL = "https://cointelegraph-cn.com/category/latest-news"
PRIMARY_NEWS_BASE_URL = "https://cointelegraph-cn.com"
BACKUP_NEWS_URL = "https://coinmarketcap.com/zh/headlines/news/"
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"
FEAR_GREED_SOURCE_URL = "https://alternative.me/crypto/fear-and-greed-index/"
DEFILLAMA_CHAINS_API_URL = "https://api.llama.fi/v2/chains"
YAHOO_CHART_API_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


@dataclass(frozen=True)
class ScriptConfig:
    """集中管理脚本配置、资源路径和运行参数。"""

    base_dir: Path = field(default_factory=lambda: PROJECT_ROOT)
    report_dir_name: str = "crypto_daily_report"
    report_output_dir: Path | None = None
    report_base_url: str = "http://18.181.194.35/crypto_daily_report/"
    report_filename_date_format: str = "%Y-%m-%d"
    latest_report_filename: str = "latest.html"
    report_stylesheet_filename: str = "report.css"
    report_template_filename: str = "report.html.j2"
    report_icon_cache_dirname: str = "assets/coin-icons"
    report_asset_url_mode: str = "relative"
    report_css_mode: str = "external"
    report_title: str = "数字货币每日分析报告"
    report_system_name: str = "数字货币每日报告生成系统"
    report_version: str = "7.0.0"
    report_timezone: str = "Asia/Shanghai"
    cleanup_days_to_keep: int = 30
    trend_data_filename: str = "trend_data.json"
    log_filename: str = "crypto_analyst.log"
    log_level: str = "INFO"
    request_timeout_seconds: int = 15
    request_retries: int = 2
    request_backoff_factor: float = 0.5
    news_request_timeout_seconds: int = 10
    article_request_timeout_seconds: int = 5
    deepseek_request_timeout_seconds: int = 30
    macro_request_timeout_seconds: int = 15
    defi_request_timeout_seconds: int = 15
    max_news_display_items: int = 10
    max_news_analysis_items: int = 30
    max_news_detail_fetches: int = 3
    max_event_watch_items: int = 6
    generate_screenshots: bool = True
    screenshot_backend: str = "auto"
    screenshot_width: int = 1200
    screenshot_timeout_seconds: int = 30
    coingecko_api: str = "https://api.coingecko.com/api/v3"
    coinmarketcap_api: str = "https://pro-api.coinmarketcap.com/v1"
    coinmarketcap_api_key: str = "replace-me"
    deepseek_api_key: str = "replace-me"
    deepseek_api_url: str = "https://api.deepseek.com/chat/completions"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __post_init__(self) -> None:
        self._validate_mode(
            "report_css_mode",
            self.report_css_mode,
            {"inline", "external"},
        )
        self._validate_mode(
            "report_asset_url_mode",
            self.report_asset_url_mode,
            {"relative", "absolute"},
        )

    @property
    def report_dir(self) -> Path:
        if self.report_output_dir is not None:
            return Path(self.report_output_dir)
        return self.base_dir / self.report_dir_name

    @property
    def normalized_report_base_url(self) -> str:
        return self.report_base_url.rstrip("/") + "/"

    @property
    def report_stylesheet_file(self) -> Path:
        return self.base_dir / "crypto_report" / "assets" / self.report_stylesheet_filename

    @property
    def report_template_file(self) -> Path:
        return self.base_dir / "crypto_report" / "templates" / self.report_template_filename

    @property
    def report_icon_cache_dir(self) -> Path:
        return self.report_dir / self.report_icon_cache_dirname

    @property
    def trend_data_file(self) -> Path:
        return self.base_dir / self.trend_data_filename

    @property
    def log_file(self) -> Path:
        return self.base_dir / self.log_filename

    def build_asset_href(self, filename: str) -> str:
        if self.should_inline_css():
            return ""
        if self.report_asset_url_mode == "absolute":
            return self.normalized_report_base_url + filename.lstrip("/")
        return filename

    def build_report_filename(self, report_date: datetime) -> str:
        return f"{report_date.strftime(self.report_filename_date_format)}.html"

    def get_report_timezone(self):
        try:
            return ZoneInfo(self.report_timezone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("Asia/Shanghai")

    def should_inline_css(self) -> bool:
        return self.report_css_mode == "inline"

    def ignores_asset_url_mode(self) -> bool:
        return self.should_inline_css()

    @staticmethod
    def _validate_mode(name: str, value: str, allowed_values: set[str]) -> None:
        if value not in allowed_values:
            allowed = ", ".join(sorted(allowed_values))
            raise ValueError(f"{name} 必须是以下值之一: {allowed}; 当前值: {value}")


def _load_overrides_from_file(config_file: Path | None) -> Dict[str, Any]:
    if config_file is None or not config_file.exists():
        return {}

    data = json.loads(config_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{config_file.name} 必须是 JSON 对象")
    return data


def _resolve_config_file(base_dir: Path, config_file: Path | None) -> Path | None:
    if config_file is not None:
        return config_file

    local_config_file = base_dir / "local_config.json"
    legacy_local_config_file = base_dir / "dashboard_local_config.json"
    if local_config_file.exists():
        return local_config_file
    if legacy_local_config_file.exists():
        return legacy_local_config_file
    return None


def load_script_config(
    base_dir: Path | None = None,
    config_file: Path | None = None,
    runtime_overrides: Dict[str, Any] | None = None,
) -> ScriptConfig:
    base_dir = base_dir or PROJECT_ROOT
    config_file = _resolve_config_file(base_dir, config_file)
    config = ScriptConfig(base_dir=base_dir)
    valid_fields = {field.name for field in fields(ScriptConfig)}
    file_overrides = _load_overrides_from_file(config_file)
    if "report_dir_override" in file_overrides and "report_output_dir" not in file_overrides:
        file_overrides["report_output_dir"] = file_overrides["report_dir_override"]
    if "report_output_dir" in file_overrides and file_overrides["report_output_dir"] is not None:
        output_dir = Path(file_overrides["report_output_dir"])
        if not output_dir.is_absolute():
            output_dir = base_dir / output_dir
        file_overrides["report_output_dir"] = output_dir

    overrides = {
        key: value
        for key, value in file_overrides.items()
        if key in valid_fields and key != "base_dir"
    }
    if runtime_overrides:
        runtime_overrides = dict(runtime_overrides)
        if (
            "report_dir_override" in runtime_overrides
            and "report_output_dir" not in runtime_overrides
        ):
            runtime_overrides["report_output_dir"] = runtime_overrides["report_dir_override"]
        if "report_output_dir" in runtime_overrides and runtime_overrides["report_output_dir"] is not None:
            runtime_overrides = dict(runtime_overrides)
            output_dir = Path(runtime_overrides["report_output_dir"])
            if not output_dir.is_absolute():
                output_dir = base_dir / output_dir
            runtime_overrides["report_output_dir"] = output_dir
        overrides.update(
            {
                key: value
                for key, value in runtime_overrides.items()
                if key in valid_fields and key != "base_dir" and value is not None
            }
        )
    if not overrides:
        return config

    data = asdict(config)
    data.update(overrides)
    data["base_dir"] = base_dir
    return ScriptConfig(**data)
