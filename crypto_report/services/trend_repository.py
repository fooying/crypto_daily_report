from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class TrendRepository:
    """Handle persistence and raw trend updates."""

    SERIES_RETENTION_LIMITS = {
        "fear_greed_index": 30,
        "market_cap": 30,
        "bitcoin_price": 30,
        "ethereum_price": 30,
    }

    TOP_LEVEL_KEY_ORDER = (
        "fear_greed_index",
        "market_cap",
        "bitcoin_price",
        "ethereum_price",
        "technical_context_cache",
        "technical_context_coingecko_capability",
        "technical_context_cmc_capability",
        "macro_context_coingecko_capability",
        "macro_context_cache",
        "defi_overview_cache",
        "last_updated",
        "metadata",
    )

    def __init__(self, trend_data_file: Path, report_date: datetime, logger) -> None:
        self.trend_data_file = Path(trend_data_file)
        self.report_date = report_date
        self.logger = logger

    def load(self) -> Dict[str, Any]:
        try:
            if self.trend_data_file.exists():
                return json.loads(self.trend_data_file.read_text(encoding="utf-8"))
        except Exception as exc:
            self.logger.warning(f"加载趋势数据失败: {exc}")

        return {
            "fear_greed_index": {},
            "market_cap": {},
            "bitcoin_price": {},
            "ethereum_price": {},
            "technical_context_cache": {},
            "technical_context_coingecko_capability": {},
            "technical_context_cmc_capability": {},
            "macro_context_coingecko_capability": {},
            "macro_context_cache": {},
            "defi_overview_cache": {},
            "last_updated": None,
            "metadata": {
                "version": "1.0",
                "created_at": str(datetime.now()),
                "description": "加密货币趋势数据存储",
            },
        }

    def save(self, data: Dict[str, Any]) -> bool:
        try:
            self.trend_data_file.parent.mkdir(parents=True, exist_ok=True)
            self._normalize_trend_data(data)
            data["last_updated"] = str(datetime.now())
            self.trend_data_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.logger.info(f"趋势数据已保存到: {self.trend_data_file}")
            return True
        except Exception as exc:
            self.logger.error(f"保存趋势数据失败: {exc}")
            return False

    def update_fear_greed_trend(self, current_value: int, classification: str) -> Dict[str, Any]:
        trend_data = self.load()
        current_date = self.report_date.strftime("%Y-%m-%d")
        fgi_history = trend_data.setdefault("fear_greed_index", {})
        existing = fgi_history.get(current_date) or {}
        payload = {
            "value": current_value,
            "classification": classification,
            "timestamp": str(int(time.time())),
            "source": "alternative.me",
        }
        changed = (
            existing.get("value") != payload["value"]
            or existing.get("classification") != payload["classification"]
        )
        fgi_history[current_date] = payload
        self._trim_history(fgi_history, limit=self.SERIES_RETENTION_LIMITS["fear_greed_index"])
        self.save(trend_data)
        if not existing:
            self.logger.info("恐惧贪婪指数已写入当日缓存: %s -> %s", current_date, current_value)
        elif changed:
            self.logger.info(
                "恐惧贪婪指数当日缓存已刷新: %s %s -> %s",
                current_date,
                existing.get("value"),
                current_value,
            )
        else:
            self.logger.info("恐惧贪婪指数当日缓存已确认最新: %s = %s", current_date, current_value)
        return trend_data

    def backfill_fear_greed_history(
        self,
        historical_data: List[Dict[str, Any]],
        source: str = "alternative.me",
    ) -> Dict[str, Any]:
        if not historical_data:
            return self.load()

        trend_data = self.load()
        fgi_history = trend_data.setdefault("fear_greed_index", {})
        inserted = 0
        updated = 0
        for item in historical_data:
            timestamp = item.get("timestamp")
            value = item.get("value")
            if timestamp is None or value is None:
                continue
            try:
                date_key = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d")
                new_payload = {
                    "value": int(value),
                    "classification": item.get("value_classification")
                    or item.get("classification", "未知"),
                    "timestamp": str(timestamp),
                    "source": source,
                }
                existing = fgi_history.get(date_key)
                if existing is None:
                    fgi_history[date_key] = new_payload
                    inserted += 1
                elif (
                    existing.get("value") != new_payload["value"]
                    or existing.get("classification") != new_payload["classification"]
                    or str(existing.get("timestamp", "")) != new_payload["timestamp"]
                    or existing.get("source") != new_payload["source"]
                ):
                    fgi_history[date_key] = new_payload
                    updated += 1
            except (TypeError, ValueError):
                continue

        if inserted or updated:
            self._trim_history(fgi_history, limit=self.SERIES_RETENTION_LIMITS["fear_greed_index"])
            self.save(trend_data)
            self.logger.info(
                "恐惧贪婪指数历史缓存已同步: 新增 %s 条，更新 %s 条",
                inserted,
                updated,
            )
        else:
            self.logger.info("恐惧贪婪指数历史缓存已存在，未新增或更新")
        return trend_data

    def update_market_data_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        trend_data = self.load()
        current_date = self.report_date.strftime("%Y-%m-%d")
        trend_data.setdefault("market_cap", {})[current_date] = {
            "value": market_data.get("total_market_cap", 0),
            "change_24h": market_data.get("market_cap_change_percentage_24h_usd", 0),
            "volume_24h": market_data.get("total_volume", 0),
            "btc_dominance": (market_data.get("market_cap_percentage") or {}).get("btc", 0),
            "eth_dominance": (market_data.get("market_cap_percentage") or {}).get("eth", 0),
            "timestamp": str(int(time.time())),
            "source": "coingecko",
        }
        self._trim_history(trend_data["market_cap"], limit=self.SERIES_RETENTION_LIMITS["market_cap"])
        self.save(trend_data)
        return trend_data

    def update_price_trend(self, symbol: str, price: float, change_24h: float) -> Dict[str, Any]:
        trend_data = self.load()
        current_date = self.report_date.strftime("%Y-%m-%d")
        key = self._price_storage_key(symbol)
        trend_data.setdefault(key, {})[current_date] = {
            "price": price,
            "change_24h": change_24h,
            "timestamp": str(int(time.time())),
            "source": "coingecko",
        }
        self._trim_history(trend_data[key], limit=self.SERIES_RETENTION_LIMITS.get(key, 30))
        self.save(trend_data)
        return trend_data

    def update_cached_snapshot(self, key: str, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        trend_data = self.load()
        trend_data[key] = {
            "payload": payload,
            "timestamp": str(int(time.time())),
            "source": source,
            "date": self.report_date.strftime("%Y-%m-%d"),
        }
        self.save(trend_data)
        return trend_data

    def get_cached_snapshot(self, key: str) -> Dict[str, Any]:
        return self.load().get(key, {}) or {}

    @staticmethod
    def _price_storage_key(symbol: str) -> str:
        symbol = symbol.lower()
        if symbol in {"bitcoin", "btc"}:
            return "bitcoin_price"
        if symbol in {"ethereum", "eth"}:
            return "ethereum_price"
        return f"{symbol}_price"

    @staticmethod
    def _trim_history(history: Dict[str, Any], limit: int = 90) -> None:
        dates = sorted(history.keys(), reverse=True)
        for old_date in dates[limit:]:
            del history[old_date]

    def _normalize_trend_data(self, data: Dict[str, Any]) -> None:
        for key, limit in self.SERIES_RETENTION_LIMITS.items():
            history = data.get(key)
            if isinstance(history, dict):
                self._trim_history(history, limit=limit)
                data[key] = dict(sorted(history.items(), key=lambda item: item[0], reverse=True))

        ordered: Dict[str, Any] = {}
        for key in self.TOP_LEVEL_KEY_ORDER:
            if key in data:
                ordered[key] = data[key]
        for key in sorted(data.keys()):
            if key not in ordered:
                value = data[key]
                if isinstance(value, dict):
                    value = dict(sorted(value.items(), key=lambda item: item[0]))
                ordered[key] = value

        data.clear()
        data.update(ordered)
