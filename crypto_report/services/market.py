from __future__ import annotations

from datetime import timedelta
import time
import math
from typing import Any, Dict, List

from ..config import (
    DEFILLAMA_CHAINS_API_URL,
    DEFILLAMA_PROTOCOLS_API_URL,
    FEAR_GREED_API_URL,
    FEAR_GREED_SOURCE_URL,
    YAHOO_CHART_API_URL,
)
from ..helpers import build_default_fear_greed_index, build_default_market_overview
from ..http_client import HTTPRequestError
from ..models import FearGreedIndex, MarketOverview
from .storage import TrendStorage


class MarketService:
    """Fetch market and fear/greed data and persist trend history."""

    CMC_TECHNICAL_IDS = {
        "BTC": 1,
        "ETH": 1027,
    }

    CLASSIFICATION_MAP = {
        "Extreme Fear": "极度恐惧",
        "Fear": "恐惧",
        "Neutral": "中性",
        "Greed": "贪婪",
        "Extreme Greed": "极度贪婪",
    }

    def __init__(self, config, http, logger, report_date, storage: TrendStorage) -> None:
        self.config = config
        self.http = http
        self.logger = logger
        self.report_date = report_date
        self.storage = storage
        self.last_market_overview_source = "unknown"
        self.last_top_cryptos_source = "unknown"
        self.last_market_history_source = "unknown"
        self.last_technical_context_source = "unknown"
        self.last_macro_context_source = "unknown"
        self.last_defi_overview_source = "unknown"

    def _default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json",
        }

    def _coinmarketcap_headers(self) -> Dict[str, str]:
        headers = self._default_headers()
        headers["X-CMC_PRO_API_KEY"] = self.config.coinmarketcap_api_key
        return headers

    def fetch_json(self, url: str, timeout: int = 15) -> Any:
        return self.http.fetch_json(url, timeout=timeout, headers=self._default_headers())

    def fetch_coinmarketcap_json(self, url: str, timeout: int = 15) -> Any:
        return self.http.fetch_json(
            url,
            timeout=timeout,
            headers=self._coinmarketcap_headers(),
        )

    def _build_fng_url(self, limit: int) -> str:
        return f"{FEAR_GREED_API_URL}?limit={limit}"

    def _fetch_fear_greed_history(self, limit: int) -> Dict[str, Any] | None:
        try:
            data = self.fetch_json(self._build_fng_url(limit), timeout=10)
        except HTTPRequestError as exc:
            self.logger.warning(
                "恐惧贪婪指数历史数据请求失败(limit=%s): %s",
                limit,
                exc,
            )
            return None
        except Exception as exc:
            self.logger.warning(
                "获取恐惧贪婪指数历史数据失败(limit=%s): %s",
                limit,
                exc,
            )
            return None

        if not isinstance(data, dict) or not data.get("data"):
            self.logger.warning("恐惧贪婪指数历史数据为空(limit=%s)", limit)
            return None
        return data

    def _build_local_fear_greed_history(self, days: int) -> List[Dict[str, Any]]:
        history = self.storage.load().get("fear_greed_index", {})
        rows = []
        for date_key in sorted(history.keys(), reverse=True)[:days]:
            item = history.get(date_key) or {}
            value = item.get("value")
            if value is None:
                continue
            rows.append(
                {
                    "value": str(value),
                    "value_classification": item.get("classification", "未知"),
                    "classification": item.get("classification", "未知"),
                    "timestamp": str(item.get("timestamp", "")),
                    "source": item.get("source", "trend_cache"),
                }
            )
        return rows

    def _has_enough_local_fear_greed_history(self, days: int) -> bool:
        history = self.storage.load().get("fear_greed_index", {})
        current_date = self.report_date.strftime("%Y-%m-%d")
        return current_date in history and len(history) >= days

    def _map_coinmarketcap_global_metrics(self, data: Dict[str, Any]) -> MarketOverview:
        metrics = data.get("data", {}) or {}
        btc_dominance = metrics.get("btc_dominance", 0.0)
        eth_dominance = metrics.get("eth_dominance", 0.0)
        total_market_cap = metrics.get("quote", {}).get("USD", {}).get("total_market_cap", 0)
        total_volume = metrics.get("quote", {}).get("USD", {}).get("total_volume_24h", 0)
        return {
            "total_market_cap": total_market_cap,
            "total_volume": total_volume,
            "active_cryptocurrencies": metrics.get("active_cryptocurrencies", 0),
            "market_cap_percentage": {
                "btc": btc_dominance,
                "eth": eth_dominance,
            },
            "alt_market_cap_percentage": max(0.0, 100.0 - btc_dominance - eth_dominance),
            "volume_to_market_cap_ratio": round(total_volume / total_market_cap * 100, 2)
            if total_market_cap
            else 0,
            "btc_dominance_daily_change": None,
            "btc_dominance_weekly_change": None,
            "market_cap_change_percentage_24h_usd": metrics.get(
                "quote", {}
            ).get("USD", {}).get("total_market_cap_yesterday_percentage_change", 0),
        }

    def _calculate_market_metric_change(self, metric_name: str, current_value: float, days: int) -> float | None:
        try:
            market_history = self.storage.load().get("market_cap", {})
            dates = sorted(market_history.keys(), reverse=True)
            if len(dates) < days:
                return None
            previous_value = market_history.get(dates[days - 1], {}).get(metric_name)
            if previous_value is None:
                return None
            return round(float(current_value) - float(previous_value), 2)
        except Exception as exc:
            self.logger.debug("计算市场指标变化失败 metric=%s days=%s err=%s", metric_name, days, exc)
            return None

    def _enrich_market_overview_trends(self, overview: MarketOverview) -> MarketOverview:
        btc_dominance = (overview.get("market_cap_percentage") or {}).get("btc", 0.0)
        overview["btc_dominance_daily_change"] = self._calculate_market_metric_change(
            "btc_dominance",
            btc_dominance,
            2,
        )
        overview["btc_dominance_weekly_change"] = self._calculate_market_metric_change(
            "btc_dominance",
            btc_dominance,
            7,
        )
        return overview

    @staticmethod
    def _calculate_moving_average(values: List[float], window: int) -> float | None:
        if len(values) < window:
            return None
        subset = values[-window:]
        return round(sum(subset) / window, 2)

    @staticmethod
    def _calculate_rsi(values: List[float], period: int = 14) -> float | None:
        if len(values) <= period:
            return None
        gains = []
        losses = []
        for previous, current in zip(values[-(period + 1):-1], values[-period:]):
            delta = current - previous
            gains.append(max(delta, 0))
            losses.append(abs(min(delta, 0)))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    @staticmethod
    def _calculate_bollinger_bands(values: List[float], window: int = 20) -> Dict[str, float] | None:
        if len(values) < window:
            return None
        subset = values[-window:]
        middle = sum(subset) / window
        variance = sum((value - middle) ** 2 for value in subset) / window
        std = variance ** 0.5
        upper = middle + 2 * std
        lower = middle - 2 * std
        latest = subset[-1]
        if latest >= upper:
            status = "接近上轨"
        elif latest <= lower:
            status = "接近下轨"
        else:
            status = "区间中部"
        return {
            "upper": round(upper, 2),
            "middle": round(middle, 2),
            "lower": round(lower, 2),
            "status": status,
        }

    @staticmethod
    def _calculate_ema(values: List[float], period: int) -> float | None:
        if len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
        return round(ema, 2)

    @classmethod
    def _calculate_macd_bias(cls, values: List[float]) -> str | None:
        ema12 = cls._calculate_ema(values, 12)
        ema26 = cls._calculate_ema(values, 26)
        if ema12 is None or ema26 is None:
            return None
        macd_line = ema12 - ema26
        if macd_line > 0:
            return "快线位于零轴上方，动能偏多"
        if macd_line < 0:
            return "快线位于零轴下方，动能偏弱"
        return "快线贴近零轴，趋势方向不明"

    @staticmethod
    def _calculate_volatility(values: List[float], window: int = 30) -> float | None:
        if len(values) < window:
            return None
        subset = values[-window:]
        returns = []
        for previous, current in zip(subset[:-1], subset[1:]):
            if previous == 0:
                continue
            returns.append((current - previous) / previous)
        if len(returns) < 2:
            return None
        mean_return = sum(returns) / len(returns)
        variance = sum((item - mean_return) ** 2 for item in returns) / len(returns)
        return round((variance ** 0.5) * 100, 2)

    def _map_coinmarketcap_listings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        for coin in data.get("data", []) or []:
            quote = coin.get("quote", {}).get("USD", {})
            result.append(
                {
                    "id": coin.get("id"),
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", "").upper(),
                    "current_price": quote.get("price", 0),
                    "market_cap": quote.get("market_cap", 0),
                    "market_cap_rank": coin.get("cmc_rank", 0),
                    "price_change_percentage_24h": quote.get("percent_change_24h", 0),
                    "price_change_percentage_7d": quote.get("percent_change_7d", 0),
                    "total_volume": quote.get("volume_24h", 0),
                    "circulating_supply": coin.get("circulating_supply", 0),
                    "fully_diluted_valuation": quote.get("fully_diluted_market_cap", 0),
                    "high_24h": quote.get("high_24h", 0),
                    "low_24h": quote.get("low_24h", 0),
                    "image": "",
                }
            )
        return result

    @staticmethod
    def _normalize_series(values: List[Any]) -> List[float]:
        series: List[float] = []
        for value in values:
            try:
                if value is None:
                    continue
                series.append(float(value))
            except (TypeError, ValueError):
                continue
        return series

    @staticmethod
    def _calculate_correlation(base_values: List[float], compare_values: List[float]) -> float | None:
        if len(base_values) < 5 or len(compare_values) < 5:
            return None
        sample_size = min(len(base_values), len(compare_values))
        x = base_values[-sample_size:]
        y = compare_values[-sample_size:]
        mean_x = sum(x) / sample_size
        mean_y = sum(y) / sample_size
        numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
        denominator_x = math.sqrt(sum((a - mean_x) ** 2 for a in x))
        denominator_y = math.sqrt(sum((b - mean_y) ** 2 for b in y))
        if denominator_x == 0 or denominator_y == 0:
            return None
        return round(numerator / (denominator_x * denominator_y), 2)

    @staticmethod
    def _calculate_period_change(values: List[float], days: int = 30) -> float | None:
        if len(values) < 2:
            return None
        lookback = min(len(values) - 1, days)
        baseline = values[-(lookback + 1)]
        latest = values[-1]
        if baseline == 0:
            return None
        return round((latest - baseline) / baseline * 100, 2)

    def _fetch_yahoo_chart_series(self, symbol: str, range_value: str = "3mo") -> List[float]:
        url = (
            f"{YAHOO_CHART_API_URL}/{symbol}"
            f"?interval=1d&range={range_value}&includePrePost=false&events=div%2Csplits"
        )
        data = self.fetch_json(url, timeout=self.config.macro_request_timeout_seconds)
        result = (((data or {}).get("chart") or {}).get("result") or [None])[0] or {}
        closes = ((((result.get("indicators") or {}).get("quote") or [None])[0] or {}).get("close") or [])
        return self._normalize_series(closes)

    def get_macro_context(self) -> Dict[str, Any]:
        try:
            btc_market_chart = self.fetch_json(
                f"{self.config.coingecko_api}/coins/bitcoin/market_chart?vs_currency=usd&days=90&interval=daily",
                timeout=self.config.macro_request_timeout_seconds,
            )
            btc_prices = self._normalize_series(
                [point[1] for point in (btc_market_chart.get("prices") or []) if isinstance(point, list) and len(point) > 1]
            )
            if len(btc_prices) < 10:
                self.last_macro_context_source = "default_empty"
                return {}

            assets = [
                ("^GSPC", "标普500"),
                ("GC=F", "黄金"),
            ]
            snapshots = []
            for symbol, label in assets:
                series = self._fetch_yahoo_chart_series(symbol)
                if len(series) < 10:
                    continue
                correlation = self._calculate_correlation(btc_prices[-30:], series[-30:])
                change_30d = self._calculate_period_change(series, days=30)
                latest = series[-1]
                if correlation is None or change_30d is None:
                    continue
                snapshots.append(
                    {
                        "symbol": symbol,
                        "label": label,
                        "latest": round(latest, 2),
                        "change_30d": change_30d,
                        "correlation_30d": correlation,
                    }
                )

            if not snapshots:
                self.last_macro_context_source = "default_empty"
                return {}

            btc_change = self._calculate_period_change(btc_prices, days=30)
            btc_snapshot = {
                "symbol": "BTC",
                "label": "比特币",
                "latest": round(btc_prices[-1], 2),
                "change_30d": btc_change if btc_change is not None else 0.0,
            }
            strongest_link = max(snapshots, key=lambda item: abs(item.get("correlation_30d", 0.0)))
            summary = (
                f"近30天 BTC 与{strongest_link['label']}的相关性为"
                f"{strongest_link['correlation_30d']:+.2f}，"
                f"更适合作为当前宏观联动的观察锚点。"
            )
            self.last_macro_context_source = "coingecko_yahoo"
            self.storage.update_cached_snapshot(
                "macro_context_cache",
                {
                    "btc": btc_snapshot,
                    "assets": snapshots,
                    "summary": summary,
                },
                source=self.last_macro_context_source,
            )
            return {
                "btc": btc_snapshot,
                "assets": snapshots,
                "summary": summary,
            }
        except HTTPRequestError as exc:
            self.logger.warning("宏观关联数据获取失败: %s", exc)
        except Exception as exc:
            self.logger.warning("宏观关联分析生成失败: %s", exc)
        cached = self.storage.get_cached_snapshot("macro_context_cache")
        payload = cached.get("payload") or {}
        if payload:
            self.last_macro_context_source = "local_cache"
            return payload
        self.last_macro_context_source = "default_empty"
        return {}

    def get_defi_overview(self) -> Dict[str, Any]:
        try:
            chains = self.fetch_json(
                DEFILLAMA_CHAINS_API_URL,
                timeout=self.config.defi_request_timeout_seconds,
            )
            if not isinstance(chains, list):
                self.last_defi_overview_source = "default_empty"
                return {}
            eligible = [
                item
                for item in chains
                if isinstance(item, dict) and item.get("tvl") not in (None, 0)
            ]
            if not eligible:
                self.last_defi_overview_source = "default_empty"
                return {}

            protocols = self.fetch_json(
                DEFILLAMA_PROTOCOLS_API_URL,
                timeout=self.config.defi_request_timeout_seconds,
            )
            top_protocols = []
            if isinstance(protocols, list):
                filtered_protocols = [
                    item
                    for item in protocols
                    if isinstance(item, dict) and float(item.get("tvl") or 0.0) > 0
                ]
                for item in sorted(
                    filtered_protocols,
                    key=lambda row: float(row.get("tvl") or 0.0),
                    reverse=True,
                )[:5]:
                    top_protocols.append(
                        {
                            "name": str(item.get("name") or "Unknown"),
                            "category": str(item.get("category") or "Other"),
                            "chain": str(item.get("chain") or "Multi-Chain"),
                            "tvl": float(item.get("tvl") or 0.0),
                            "change_1d": float(item["change_1d"]) if item.get("change_1d") is not None else None,
                            "change_7d": float(item["change_7d"]) if item.get("change_7d") is not None else None,
                        }
                    )

            total_tvl = sum(float(item.get("tvl") or 0.0) for item in eligible)
            top_chains = sorted(
                eligible,
                key=lambda item: float(item.get("tvl") or 0.0),
                reverse=True,
            )[:4]
            chain_rows = []
            for item in top_chains:
                tvl = float(item.get("tvl") or 0.0)
                chain_rows.append(
                    {
                        "name": str(item.get("name") or item.get("gecko_id") or "Unknown"),
                        "tvl": tvl,
                        "share_pct": round(tvl / total_tvl * 100, 1) if total_tvl else 0.0,
                        "change_1d": float(item["change_1d"]) if item.get("change_1d") is not None else None,
                        "change_7d": float(item["change_7d"]) if item.get("change_7d") is not None else None,
                    }
                )
            leader = chain_rows[0]
            summary = (
                f"DeFi TVL 仍以{leader['name']}为核心，约占整体 {leader['share_pct']:.1f}% ，"
                "可结合链级别资金迁移观察风险偏好的扩散方向。"
            )
            self.last_defi_overview_source = "defillama_chains"
            payload = {
                "total_tvl": total_tvl,
                "change_1d": None,
                "change_7d": None,
                "top_chains": chain_rows,
                "top_protocols": top_protocols,
                "summary": summary,
            }
            self.storage.update_cached_snapshot(
                "defi_overview_cache",
                payload,
                source=self.last_defi_overview_source,
            )
            return payload
        except HTTPRequestError as exc:
            self.logger.warning("DeFi 概览数据获取失败: %s", exc)
        except Exception as exc:
            self.logger.warning("DeFi 概览生成失败: %s", exc)
        cached = self.storage.get_cached_snapshot("defi_overview_cache")
        payload = cached.get("payload") or {}
        if payload:
            self.last_defi_overview_source = "local_cache"
            return payload
        self.last_defi_overview_source = "default_empty"
        return {}

    def _fetch_coinmarketcap_logos(
        self,
        coins: List[Dict[str, Any]],
    ) -> Dict[int, str]:
        coin_ids = [str(coin.get("id")) for coin in coins if coin.get("id")]
        if not coin_ids:
            return {}

        info_url = (
            f"{self.config.coinmarketcap_api}/cryptocurrency/info"
            f"?id={','.join(coin_ids)}"
        )
        info_data = self.fetch_coinmarketcap_json(info_url, timeout=15)
        logo_map: Dict[int, str] = {}
        for coin_id, info in (info_data.get("data") or {}).items():
            try:
                logo_map[int(coin_id)] = str(info.get("logo", "")).strip()
            except (TypeError, ValueError):
                continue
        return logo_map

    def _apply_coinmarketcap_logos(
        self,
        coins: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not coins:
            return coins

        try:
            logo_map = self._fetch_coinmarketcap_logos(coins)
        except HTTPRequestError as exc:
            self.logger.warning("CoinMarketCap 币种 logo 请求失败: %s", exc)
            return coins
        except Exception as exc:
            self.logger.warning("CoinMarketCap 币种 logo 获取失败: %s", exc)
            return coins

        for coin in coins:
            coin_id = coin.get("id")
            if coin_id in logo_map and logo_map[coin_id]:
                coin["image"] = logo_map[coin_id]
        return coins

    def _format_cmc_datetime(self, value) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S")

    def _try_primary_then_backup(
        self,
        *,
        primary_fn,
        backup_fn,
        last_source_attr: str,
        empty_result,
        primary_label: str,
        backup_label: str,
        log_prefix: str,
    ):
        try:
            result = primary_fn()
            setattr(self, last_source_attr, primary_label)
            return result
        except HTTPRequestError as exc:
            self.logger.warning("%s 主源请求失败，尝试备用源: %s", log_prefix, exc)
        except Exception as exc:
            self.logger.warning("%s 主源获取失败，尝试备用源: %s", log_prefix, exc)

        try:
            result = backup_fn()
            setattr(self, last_source_attr, backup_label)
            self.logger.info("%s 已切换为备用源", log_prefix)
            return result
        except HTTPRequestError as exc:
            self.logger.warning("%s 备用源请求失败: %s", log_prefix, exc)
        except Exception as exc:
            self.logger.warning("%s 备用源获取失败: %s", log_prefix, exc)

        self.logger.error("%s 获取失败，返回默认数据", log_prefix)
        setattr(self, last_source_attr, "default_empty")
        return empty_result

    def get_market_cap_history(self, days: int = 30) -> List[Dict[str, Any]]:
        try:
            trend_data = self.storage.load().get("market_cap", {})
            dates = sorted(trend_data.keys())
            result = []
            for date_key in dates[-days:]:
                item = trend_data.get(date_key) or {}
                market_cap = item.get("value")
                volume_24h = item.get("volume_24h")
                if market_cap is None or volume_24h is None:
                    continue
                result.append(
                    {
                        "timestamp": f"{date_key}T00:00:00",
                        "market_cap": float(market_cap),
                        "volume_24h": float(volume_24h),
                    }
                )
            if result:
                self.last_market_history_source = "local_trend_cache"
                return result
            self.last_market_history_source = "default_empty"
            return []
        except Exception as exc:
            self.logger.warning("本地市值历史数据读取失败: %s", exc)
        self.last_market_history_source = "default_empty"
        return []

    def _build_technical_context_from_series(
        self,
        close_prices: List[float],
        volume_values: List[float],
    ) -> Dict[str, Any]:
        ma7 = self._calculate_moving_average(close_prices, 7)
        ma30 = self._calculate_moving_average(close_prices, 30)
        rsi14 = self._calculate_rsi(close_prices, 14)
        bollinger = self._calculate_bollinger_bands(close_prices, 20) or {}
        return {
            "price_change_30d": round(
                (close_prices[-1] - close_prices[0]) / close_prices[0] * 100,
                2,
            )
            if close_prices[0]
            else 0,
            "high_30d": max(close_prices),
            "low_30d": min(close_prices),
            "latest_close": close_prices[-1],
            "avg_volume_30d": round(sum(volume_values) / len(volume_values), 2)
            if volume_values
            else 0,
            "ma7": ma7,
            "ma30": ma30,
            "rsi14": rsi14,
            "bollinger_upper": bollinger.get("upper"),
            "bollinger_middle": bollinger.get("middle"),
            "bollinger_lower": bollinger.get("lower"),
            "bollinger_status": bollinger.get("status", ""),
            "macd_bias": self._calculate_macd_bias(close_prices),
            "volatility_30d": self._calculate_volatility(close_prices, 30),
            "support_level": round(min(close_prices[-7:]), 2) if len(close_prices) >= 7 else None,
            "resistance_level": round(max(close_prices[-7:]), 2) if len(close_prices) >= 7 else None,
        }

    def _fetch_coinmarketcap_technical_context(
        self,
        time_start,
        time_end,
    ) -> Dict[str, Any]:
        if not self.config.coinmarketcap_api_key or self.config.coinmarketcap_api_key == "replace-me":
            return {}

        context: Dict[str, Any] = {}
        for label, cmc_id in self.CMC_TECHNICAL_IDS.items():
            url = (
                f"{self.config.coinmarketcap_api}/cryptocurrency/ohlcv/historical"
                f"?id={cmc_id}"
                f"&time_start={time_start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                f"&time_end={time_end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                "&interval=daily&count=31&convert=USD"
            )
            data = self.fetch_coinmarketcap_json(url, timeout=15)
            quotes = (((data or {}).get("data") or {}).get("quotes")) or []
            close_prices: List[float] = []
            volume_values: List[float] = []
            for item in quotes:
                quote = (item or {}).get("quote", {}).get("USD", {})
                close = quote.get("close")
                volume = quote.get("volume")
                if close is None:
                    continue
                close_prices.append(float(close))
                if volume is not None:
                    volume_values.append(float(volume))
            if len(close_prices) < 2:
                continue
            context[label] = self._build_technical_context_from_series(close_prices, volume_values)
        return context

    def get_technical_context(self) -> Dict[str, Any]:
        time_end = self.report_date
        time_start = time_end - timedelta(days=30)

        try:
            context: Dict[str, Any] = {}
            range_from = int(time_start.timestamp())
            range_to = int(time_end.timestamp())

            for asset_id, label in (("bitcoin", "BTC"), ("ethereum", "ETH")):
                url = (
                    f"{self.config.coingecko_api}/coins/{asset_id}/market_chart/range"
                    f"?vs_currency=usd&from={range_from}&to={range_to}"
                )
                data = self.fetch_json(url, timeout=15)
                prices = data.get("prices") or []
                volumes = data.get("total_volumes") or []
                if not prices:
                    continue

                close_prices = []
                volume_values = []
                for point in prices:
                    if not isinstance(point, list) or len(point) < 2 or point[1] is None:
                        continue
                    close_prices.append(float(point[1]))

                for point in volumes:
                    if not isinstance(point, list) or len(point) < 2 or point[1] is None:
                        continue
                    volume_values.append(float(point[1]))

                if not close_prices:
                    continue
                context[label] = self._build_technical_context_from_series(close_prices, volume_values)
            if context:
                self.last_technical_context_source = "coingecko_market_chart_range"
                return context
        except HTTPRequestError as exc:
            self.logger.warning("CoinGecko 技术背景历史请求失败，尝试 CoinMarketCap 备用源: %s", exc)
        except Exception as exc:
            self.logger.warning("CoinGecko 技术背景历史获取失败，尝试 CoinMarketCap 备用源: %s", exc)

        try:
            context = self._fetch_coinmarketcap_technical_context(time_start, time_end)
            if context:
                self.last_technical_context_source = "coinmarketcap_ohlcv_historical"
                self.logger.info("技术背景摘要已切换为 CoinMarketCap 备用源")
                return context
        except HTTPRequestError as exc:
            self.logger.warning("CoinMarketCap 技术背景历史请求失败，技术背景摘要将降级为空: %s", exc)
        except Exception as exc:
            self.logger.warning("CoinMarketCap 技术背景历史获取失败，技术背景摘要将降级为空: %s", exc)
        self.last_technical_context_source = "default_empty"
        return {}

    def get_market_overview(self) -> MarketOverview:
        def primary():
            data = self.fetch_json(f"{self.config.coingecko_api}/global", timeout=15)
            if "data" not in data:
                raise ValueError("global 接口缺少 data 字段")
            market_data = data["data"]
            total_market_cap = market_data.get("total_market_cap", {}).get("usd", 0)
            total_volume = market_data.get("total_volume", {}).get("usd", 0)
            btc_dominance = market_data.get("market_cap_percentage", {}).get("btc", 0)
            eth_dominance = market_data.get("market_cap_percentage", {}).get("eth", 0)
            result: MarketOverview = {
                "total_market_cap": total_market_cap,
                "total_volume": total_volume,
                "active_cryptocurrencies": market_data.get("active_cryptocurrencies", 0),
                "market_cap_percentage": market_data.get("market_cap_percentage", {}),
                "alt_market_cap_percentage": max(0.0, 100.0 - btc_dominance - eth_dominance),
                "volume_to_market_cap_ratio": round(total_volume / total_market_cap * 100, 2)
                if total_market_cap
                else 0,
                "btc_dominance_daily_change": None,
                "btc_dominance_weekly_change": None,
                "market_cap_change_percentage_24h_usd": market_data.get(
                    "market_cap_change_percentage_24h_usd", 0
                ),
            }
            self.storage.update_market_data_trend(result)
            return self._enrich_market_overview_trends(result)

        def backup():
            fallback_data = self.fetch_coinmarketcap_json(
                f"{self.config.coinmarketcap_api}/global-metrics/quotes/latest",
                timeout=15,
            )
            result = self._map_coinmarketcap_global_metrics(fallback_data)
            self.storage.update_market_data_trend(result)
            return self._enrich_market_overview_trends(result)

        return self._try_primary_then_backup(
            primary_fn=primary,
            backup_fn=backup,
            last_source_attr="last_market_overview_source",
            empty_result=build_default_market_overview(),
            primary_label="coingecko_primary",
            backup_label="coinmarketcap_backup",
            log_prefix="市场概览",
        )

    def get_top_cryptocurrencies(self, limit: int = 10) -> List[Dict[str, Any]]:
        def primary():
            url = (
                f"{self.config.coingecko_api}/coins/markets?vs_currency=usd&order=market_cap_desc"
                f"&per_page={limit}&page=1&sparkline=true&price_change_percentage=7d"
            )
            coins = self.fetch_json(url, timeout=15)
            result = []
            for coin in coins:
                result.append(
                    {
                        "id": coin.get("id"),
                        "name": coin.get("name", ""),
                        "symbol": coin.get("symbol", "").upper(),
                        "current_price": coin.get("current_price", 0),
                        "market_cap": coin.get("market_cap", 0),
                        "market_cap_rank": coin.get("market_cap_rank", 0),
                        "price_change_percentage_24h": coin.get("price_change_percentage_24h", 0),
                        "price_change_percentage_7d": coin.get("price_change_percentage_7d_in_currency", 0),
                        "total_volume": coin.get("total_volume", 0),
                        "circulating_supply": coin.get("circulating_supply", 0),
                        "fully_diluted_valuation": coin.get("fully_diluted_valuation", 0),
                        "high_24h": coin.get("high_24h", 0),
                        "low_24h": coin.get("low_24h", 0),
                        "image": coin.get("image", ""),
                        "sparkline_7d": (coin.get("sparkline_in_7d") or {}).get("price", []),
                    }
                )
            return result

        def backup():
            fallback_url = (
                f"{self.config.coinmarketcap_api}/cryptocurrency/listings/latest"
                f"?convert=USD&limit={limit}&sort=market_cap"
            )
            fallback_data = self.fetch_coinmarketcap_json(fallback_url, timeout=15)
            result = self._map_coinmarketcap_listings(fallback_data)
            return self._apply_coinmarketcap_logos(result)

        return self._try_primary_then_backup(
            primary_fn=primary,
            backup_fn=backup,
            last_source_attr="last_top_cryptos_source",
            empty_result=[],
            primary_label="coingecko_primary",
            backup_label="coinmarketcap_backup",
            log_prefix="主要加密货币",
        )

    @staticmethod
    def _calculate_change_from_history(
        current_value: int,
        data: Dict[str, Any] | None,
        index: int,
    ) -> int | None:
        history = (data or {}).get("data", [])
        if len(history) <= index:
            return None
        return current_value - int(history[index]["value"])

    def parse_fear_greed_response(
        self,
        data: Dict[str, Any],
        limit: int = 7,
        history_7d: Dict[str, Any] | None = None,
        history_30d: Dict[str, Any] | None = None,
        persist_current: bool = True,
    ) -> FearGreedIndex:
        if not data or "data" not in data or not data["data"]:
            raise ValueError("恐惧贪婪接口返回为空")

        current_item = data["data"][0]
        current_value = int(current_item["value"])
        classification = self.CLASSIFICATION_MAP.get(
            current_item.get("value_classification", ""),
            current_item.get("value_classification", ""),
        )
        self.logger.info(f"获取恐惧贪婪指数成功: {current_value} ({classification})")
        if persist_current:
            self.storage.update_fear_greed_trend(current_value, classification)
        self.storage.backfill_fear_greed_history(data.get("data", []), source="alternative.me")
        if history_7d is not None and history_7d is not data:
            self.storage.backfill_fear_greed_history(
                history_7d.get("data", []),
                source="alternative.me",
            )
        if history_30d is not None and history_30d is not data and history_30d is not history_7d:
            self.storage.backfill_fear_greed_history(
                history_30d.get("data", []),
                source="alternative.me",
            )

        seven_day_history = history_7d or (data if len(data["data"]) >= 7 else None)
        thirty_day_history = history_30d or (data if len(data["data"]) >= 30 else None)

        daily_change = None
        if len(data["data"]) >= 2:
            daily_change = current_value - int(data["data"][1]["value"])
            self.logger.info(f"使用API历史数据计算日度变化: {daily_change}")

        weekly_change = self._calculate_change_from_history(
            current_value,
            seven_day_history,
            6,
        )
        if weekly_change is not None:
            self.logger.info(f"使用7天历史数据计算周度变化: {weekly_change}")

        if weekly_change is None:
            weekly_change = self.storage.calculate_weekly_change_from_trend(current_value)
            if weekly_change is not None:
                self.logger.info(f"使用本地趋势数据计算周度变化: {weekly_change}")

        monthly_change = self._calculate_change_from_history(
            current_value,
            thirty_day_history,
            29,
        )
        if monthly_change is not None:
            self.logger.info(f"使用30天历史数据计算月度变化: {monthly_change}")
        if monthly_change is None:
            monthly_change = self.storage.calculate_change_from_trend(current_value, days=30)
            if monthly_change is not None:
                self.logger.info(f"使用本地趋势数据计算月度变化: {monthly_change}")

        historical_data = None
        if limit > 1:
            if thirty_day_history is not None:
                historical_data = thirty_day_history["data"]
            elif history_7d is not None:
                historical_data = history_7d["data"]
            else:
                historical_data = data["data"]

        if historical_data is None or len(historical_data) < min(limit, 30):
            local_history_limit = 30 if limit >= 30 else max(limit, 7)
            local_history = self._build_local_fear_greed_history(local_history_limit)
            if len(local_history) > len(historical_data or []):
                historical_data = local_history

        return {
            "value": current_value,
            "classification": classification,
            "timestamp": current_item["timestamp"],
            "time_until_update": current_item.get("time_until_update", ""),
            "source": "alternative.me",
            "url": FEAR_GREED_SOURCE_URL,
            "daily_change": daily_change,
            "weekly_change": weekly_change,
            "monthly_change": monthly_change,
            "historical_data": historical_data,
        }

    def get_fear_greed_index(self, limit: int = 7) -> FearGreedIndex:
        try:
            request_limit = max(limit, 2)
            data = self.fetch_json(self._build_fng_url(request_limit), timeout=10)
            history_7d = data if len(data.get("data", [])) >= 7 else None
            history_30d = data if len(data.get("data", [])) >= 30 else None

            current_item = data.get("data", [{}])[0]
            current_value = int(current_item["value"])
            classification = self.CLASSIFICATION_MAP.get(
                current_item.get("value_classification", ""),
                current_item.get("value_classification", ""),
            )
            self.storage.update_fear_greed_trend(current_value, classification)

            if history_7d is None and not self._has_enough_local_fear_greed_history(7):
                history_7d = self._fetch_fear_greed_history(7)
            if history_30d is None and not self._has_enough_local_fear_greed_history(30):
                history_30d = self._fetch_fear_greed_history(30)

            return self.parse_fear_greed_response(
                data,
                limit=limit,
                history_7d=history_7d,
                history_30d=history_30d,
                persist_current=False,
            )
        except HTTPRequestError as exc:
            self.logger.warning("恐惧贪婪指数请求失败: %s", exc)
        except Exception as exc:
            self.logger.warning("获取恐惧贪婪指数失败: %s", exc)
        self.logger.warning("API调用失败，尝试从趋势数据获取")
        fgi_trend = self.storage.load().get("fear_greed_index", {})
        dates = sorted(fgi_trend.keys(), reverse=True)
        if dates:
            latest_data = fgi_trend[dates[0]]
            return {
                "value": latest_data["value"],
                "classification": latest_data["classification"],
                "timestamp": str(int(time.time())),
                "time_until_update": "3600",
                "source": "trend_cache",
                "url": FEAR_GREED_SOURCE_URL,
                "daily_change": None,
                "weekly_change": None,
                "monthly_change": None,
                "historical_data": None,
            }
        return build_default_fear_greed_index()
