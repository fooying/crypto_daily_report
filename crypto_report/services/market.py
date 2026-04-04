from __future__ import annotations

from datetime import timedelta
import time
from typing import Any, Dict, List

from ..config import FEAR_GREED_API_URL, FEAR_GREED_SOURCE_URL
from ..helpers import build_default_fear_greed_index, build_default_market_overview
from ..http_client import HTTPRequestError
from ..models import FearGreedIndex, MarketOverview
from .storage import TrendStorage


class MarketService:
    """Fetch market and fear/greed data and persist trend history."""

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

    def _map_coinmarketcap_global_metrics(self, data: Dict[str, Any]) -> MarketOverview:
        metrics = data.get("data", {}) or {}
        btc_dominance = metrics.get("btc_dominance", 0.0)
        eth_dominance = metrics.get("eth_dominance", 0.0)
        return {
            "total_market_cap": metrics.get("quote", {}).get("USD", {}).get("total_market_cap", 0),
            "total_volume": metrics.get("quote", {}).get("USD", {}).get("total_volume_24h", 0),
            "active_cryptocurrencies": metrics.get("active_cryptocurrencies", 0),
            "market_cap_percentage": {
                "btc": btc_dominance,
                "eth": eth_dominance,
            },
            "market_cap_change_percentage_24h_usd": metrics.get(
                "quote", {}
            ).get("USD", {}).get("total_market_cap_yesterday_percentage_change", 0),
        }

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
                    "image": "",
                }
            )
        return result

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
        time_end = self.report_date
        time_start = time_end - timedelta(days=days)
        url = (
            f"{self.config.coinmarketcap_api}/global-metrics/quotes/historical"
            f"?convert=USD&time_start={self._format_cmc_datetime(time_start)}"
            f"&time_end={self._format_cmc_datetime(time_end)}&interval=1d"
        )
        try:
            data = self.fetch_coinmarketcap_json(url, timeout=15)
            quotes = (data.get("data") or {}).get("quotes", [])
            result = []
            for item in quotes:
                usd = (item.get("quote") or {}).get("USD", {})
                market_cap = usd.get("total_market_cap")
                volume_24h = usd.get("total_volume_24h")
                timestamp = item.get("timestamp")
                if market_cap is None or volume_24h is None or timestamp is None:
                    continue
                result.append(
                    {
                        "timestamp": timestamp,
                        "market_cap": float(market_cap),
                        "volume_24h": float(volume_24h),
                    }
                )
            if result:
                self.last_market_history_source = "coinmarketcap_historical"
            return result
        except HTTPRequestError as exc:
            self.logger.warning("CoinMarketCap 市值历史请求失败: %s", exc)
        except Exception as exc:
            self.logger.warning("CoinMarketCap 市值历史获取失败: %s", exc)
        self.last_market_history_source = "default_empty"
        return []

    def get_technical_context(self) -> Dict[str, Any]:
        time_end = self.report_date
        time_start = time_end - timedelta(days=30)
        url = (
            f"{self.config.coinmarketcap_api}/cryptocurrency/ohlcv/historical"
            f"?id=1,1027&convert=USD&time_start={self._format_cmc_datetime(time_start)}"
            f"&time_end={self._format_cmc_datetime(time_end)}&interval=daily"
        )
        try:
            data = self.fetch_coinmarketcap_json(url, timeout=15)
            raw_data = data.get("data") or {}
            context: Dict[str, Any] = {}
            for key, label in (("1", "BTC"), ("1027", "ETH")):
                asset = raw_data.get(key) or {}
                quotes = asset.get("quotes") or []
                if not quotes:
                    continue
                prices = []
                volumes = []
                for quote in quotes:
                    usd = (quote.get("quote") or {}).get("USD", {})
                    close = usd.get("close")
                    volume = usd.get("volume")
                    if close is None:
                        continue
                    prices.append(float(close))
                    if volume is not None:
                        volumes.append(float(volume))
                if not prices:
                    continue
                context[label] = {
                    "price_change_30d": round((prices[-1] - prices[0]) / prices[0] * 100, 2),
                    "high_30d": max(prices),
                    "low_30d": min(prices),
                    "latest_close": prices[-1],
                    "avg_volume_30d": round(sum(volumes) / len(volumes), 2) if volumes else 0,
                }
            if context:
                self.last_technical_context_source = "coinmarketcap_ohlcv"
            return context
        except HTTPRequestError as exc:
            self.logger.warning("CoinMarketCap OHLCV 历史请求失败: %s", exc)
        except Exception as exc:
            self.logger.warning("CoinMarketCap OHLCV 历史获取失败: %s", exc)
        self.last_technical_context_source = "default_empty"
        return {}

    def get_market_overview(self) -> MarketOverview:
        def primary():
            data = self.fetch_json(f"{self.config.coingecko_api}/global", timeout=15)
            if "data" not in data:
                raise ValueError("global 接口缺少 data 字段")
            market_data = data["data"]
            result: MarketOverview = {
                "total_market_cap": market_data.get("total_market_cap", {}).get("usd", 0),
                "total_volume": market_data.get("total_volume", {}).get("usd", 0),
                "active_cryptocurrencies": market_data.get("active_cryptocurrencies", 0),
                "market_cap_percentage": market_data.get("market_cap_percentage", {}),
                "market_cap_change_percentage_24h_usd": market_data.get(
                    "market_cap_change_percentage_24h_usd", 0
                ),
            }
            self.storage.update_market_data_trend(result)
            return result

        def backup():
            fallback_data = self.fetch_coinmarketcap_json(
                f"{self.config.coinmarketcap_api}/global-metrics/quotes/latest",
                timeout=15,
            )
            result = self._map_coinmarketcap_global_metrics(fallback_data)
            self.storage.update_market_data_trend(result)
            return result

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
                f"&per_page={limit}&page=1&sparkline=false&price_change_percentage=7d"
            )
            coins = self.fetch_json(url, timeout=15)
            result = []
            for coin in coins:
                result.append(
                    {
                        "name": coin.get("name", ""),
                        "symbol": coin.get("symbol", "").upper(),
                        "current_price": coin.get("current_price", 0),
                        "market_cap": coin.get("market_cap", 0),
                        "market_cap_rank": coin.get("market_cap_rank", 0),
                        "price_change_percentage_24h": coin.get("price_change_percentage_24h", 0),
                        "price_change_percentage_7d": coin.get("price_change_percentage_7d_in_currency", 0),
                        "total_volume": coin.get("total_volume", 0),
                        "circulating_supply": coin.get("circulating_supply", 0),
                        "image": coin.get("image", ""),
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
            local_fgi_history = self.storage.load().get("fear_greed_index", {})
            history_7d = data if len(data.get("data", [])) >= 7 else None
            history_30d = data if len(data.get("data", [])) >= 30 else None

            if len(local_fgi_history) < 7 and history_7d is None:
                history_7d = self._fetch_fear_greed_history(7)
            if len(local_fgi_history) < 30 and history_30d is None:
                history_30d = self._fetch_fear_greed_history(30)

            return self.parse_fear_greed_response(
                data,
                limit=limit,
                history_7d=history_7d,
                history_30d=history_30d,
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
