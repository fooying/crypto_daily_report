from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
import threading
from typing import Any, Dict, List


class TrendRepository:
    """Handle persistence and raw trend updates."""

    _LOCKS_GUARD = threading.Lock()
    _FILE_LOCKS: Dict[str, threading.RLock] = {}

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
        self._file_lock = self._get_file_lock(self.trend_data_file)
        self._ensure_primary_file_health()

    def load(self) -> Dict[str, Any]:
        with self._file_lock:
            return self._load_unlocked()

    def save(self, data: Dict[str, Any]) -> bool:
        with self._file_lock:
            return self._save_unlocked(data)

    def update_fear_greed_trend(self, current_value: int, classification: str) -> Dict[str, Any]:
        with self._file_lock:
            trend_data = self._load_unlocked()
            current_date = self.report_date.strftime("%Y-%m-%d")
            fgi_history = trend_data.setdefault("fear_greed_index", {})
            existing = fgi_history.get(current_date) or {}
            changed = (
                existing.get("value") != current_value
                or existing.get("classification") != classification
            )
            if changed or not existing:
                fgi_history[current_date] = {
                    "value": current_value,
                    "classification": classification,
                    "timestamp": str(int(time.time())),
                    "source": "alternative.me",
                }
                self._trim_history(fgi_history, limit=self.SERIES_RETENTION_LIMITS["fear_greed_index"])
                self._save_unlocked(trend_data)
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

        with self._file_lock:
            trend_data = self._load_unlocked()
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
                self._save_unlocked(trend_data)
        if inserted or updated:
            self.logger.info(
                "恐惧贪婪指数历史缓存已同步: 新增 %s 条，更新 %s 条",
                inserted,
                updated,
            )
        else:
            self.logger.info("恐惧贪婪指数历史缓存已存在，未新增或更新")
        return trend_data

    def update_market_data_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        with self._file_lock:
            trend_data = self._load_unlocked()
            current_date = self.report_date.strftime("%Y-%m-%d")
            payload = {
                "value": market_data.get("total_market_cap", 0),
                "change_24h": market_data.get("market_cap_change_percentage_24h_usd", 0),
                "volume_24h": market_data.get("total_volume", 0),
                "btc_dominance": (market_data.get("market_cap_percentage") or {}).get("btc", 0),
                "eth_dominance": (market_data.get("market_cap_percentage") or {}).get("eth", 0),
                "timestamp": str(int(time.time())),
                "source": "coingecko",
            }
            history = trend_data.setdefault("market_cap", {})
            existing = history.get(current_date) or {}
            changed = any(
                existing.get(field) != payload[field]
                for field in ("value", "change_24h", "volume_24h", "btc_dominance", "eth_dominance", "source")
            )
            if changed or not existing:
                history[current_date] = payload
                self._trim_history(history, limit=self.SERIES_RETENTION_LIMITS["market_cap"])
                self._save_unlocked(trend_data)
            return trend_data

    def update_price_trend(self, symbol: str, price: float, change_24h: float) -> Dict[str, Any]:
        with self._file_lock:
            trend_data = self._load_unlocked()
            current_date = self.report_date.strftime("%Y-%m-%d")
            key = self._price_storage_key(symbol)
            payload = {
                "price": price,
                "change_24h": change_24h,
                "timestamp": str(int(time.time())),
                "source": "coingecko",
            }
            history = trend_data.setdefault(key, {})
            existing = history.get(current_date) or {}
            changed = any(
                existing.get(field) != payload[field]
                for field in ("price", "change_24h", "source")
            )
            if changed or not existing:
                history[current_date] = payload
                self._trim_history(history, limit=self.SERIES_RETENTION_LIMITS.get(key, 30))
                self._save_unlocked(trend_data)
            return trend_data

    def update_cached_snapshot(self, key: str, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        with self._file_lock:
            trend_data = self._load_unlocked()
            current_date = self.report_date.strftime("%Y-%m-%d")
            existing = trend_data.get(key) or {}
            changed = (
                existing.get("payload") != payload
                or existing.get("source") != source
                or existing.get("date") != current_date
            )
            if changed:
                trend_data[key] = {
                    "payload": payload,
                    "timestamp": str(int(time.time())),
                    "source": source,
                    "date": current_date,
                }
                self._save_unlocked(trend_data)
            return trend_data

    def get_cached_snapshot(self, key: str) -> Dict[str, Any]:
        with self._file_lock:
            return deepcopy((self._load_unlocked().get(key, {}) or {}))

    def _load_unlocked(self) -> Dict[str, Any]:
        try:
            if self.trend_data_file.exists():
                data = json.loads(self.trend_data_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    normalized = deepcopy(data)
                    self._normalize_trend_data(normalized)
                    if self._snapshot_without_last_updated(normalized) != self._snapshot_without_last_updated(data):
                        self.logger.info("趋势数据检测到可整理内容，已自动重写: %s", self.trend_data_file)
                        self._save_unlocked(normalized)
                        return normalized
                    return data
        except Exception as exc:
            self.logger.warning("加载趋势数据失败(%s): %s", self.trend_data_file, exc)
            backup_data = self._load_backup_unlocked()
            if backup_data is not None:
                self._restore_primary_from_backup_unlocked(backup_data, reason="load_failure")
                return backup_data
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

    def _save_unlocked(self, data: Dict[str, Any]) -> bool:
        try:
            self.trend_data_file.parent.mkdir(parents=True, exist_ok=True)
            self._normalize_trend_data(data)
            current_snapshot = self._snapshot_without_last_updated(data)
            existing_snapshot = self._load_snapshot_without_last_updated()
            if existing_snapshot == current_snapshot:
                self.logger.debug("趋势数据无变化，跳过保存: %s", self.trend_data_file)
                return False

            data["last_updated"] = str(datetime.now())
            serialized = json.dumps(data, ensure_ascii=False, indent=2)
            self._atomic_write(serialized)
            self.logger.debug("趋势数据已保存到: %s", self.trend_data_file)
            return True
        except Exception as exc:
            self.logger.error(f"保存趋势数据失败: {exc}")
            return False

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

    def _snapshot_without_last_updated(self, data: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = deepcopy(data)
        snapshot.pop("last_updated", None)
        return snapshot

    def _load_snapshot_without_last_updated(self) -> Dict[str, Any] | None:
        try:
            if not self.trend_data_file.exists():
                return None
            existing = json.loads(self.trend_data_file.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                existing.pop("last_updated", None)
                return existing
        except Exception:
            return None
        return None

    @classmethod
    def _get_file_lock(cls, trend_data_file: Path) -> threading.RLock:
        lock_key = str(Path(trend_data_file).resolve())
        with cls._LOCKS_GUARD:
            lock = cls._FILE_LOCKS.get(lock_key)
            if lock is None:
                lock = threading.RLock()
                cls._FILE_LOCKS[lock_key] = lock
            return lock

    def _backup_path(self) -> Path:
        return self.trend_data_file.with_suffix(self.trend_data_file.suffix + ".bak")

    def _load_backup_unlocked(self) -> Dict[str, Any] | None:
        backup_path = self._backup_path()
        if not backup_path.exists():
            return None
        try:
            backup = json.loads(backup_path.read_text(encoding="utf-8"))
            if isinstance(backup, dict):
                return backup
        except Exception as exc:
            self.logger.warning("加载趋势数据备份失败: %s", exc)
        return None

    def _ensure_primary_file_health(self) -> None:
        with self._file_lock:
            if not self.trend_data_file.exists():
                return
            try:
                content = self.trend_data_file.read_text(encoding="utf-8")
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("主文件不是 JSON 对象")
            except Exception as exc:
                backup_data = self._load_backup_unlocked()
                if backup_data is None:
                    self.logger.warning("趋势数据启动自检失败且无可用备份: %s", exc)
                    return
                self._restore_primary_from_backup_unlocked(backup_data, reason=f"startup_repair:{exc}")

    def _restore_primary_from_backup_unlocked(self, backup_data: Dict[str, Any], reason: str) -> None:
        normalized = deepcopy(backup_data)
        self._normalize_trend_data(normalized)
        serialized = json.dumps(normalized, ensure_ascii=False, indent=2)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.trend_data_file.parent,
            prefix=f"{self.trend_data_file.name}.repair.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)
        os.replace(temp_path, self.trend_data_file)
        self.logger.warning(
            "趋势数据主文件已自动从备份恢复(%s): %s <- %s",
            reason,
            self.trend_data_file,
            self._backup_path(),
        )

    def _atomic_write(self, serialized: str) -> None:
        backup_path = self._backup_path()
        if self.trend_data_file.exists():
            try:
                backup_path.write_text(self.trend_data_file.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception as exc:
                self.logger.warning("刷新趋势数据备份失败: %s", exc)

        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.trend_data_file.parent,
            prefix=f"{self.trend_data_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, self.trend_data_file)
