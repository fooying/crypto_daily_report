from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import ScriptConfig


@dataclass
class HTTPRequestError(RuntimeError):
    url: str
    reason: str
    status_code: Optional[int] = None

    def __str__(self) -> str:
        status = f' status={self.status_code}' if self.status_code is not None else ''
        return f'{self.reason}: {self.url}{status}'


class HTTPClient:
    def __init__(self, config: ScriptConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.session = self._build_session()

    def _build_session(self) -> Session:
        session = requests.Session()
        retry = Retry(
            total=self.config.request_retries,
            read=self.config.request_retries,
            connect=self.config.request_retries,
            backoff_factor=self.config.request_backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({'User-Agent': self.config.user_agent})
        return session

    def fetch_json(
        self,
        url: str,
        *,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        response = self.fetch_response(
            url,
            timeout=timeout,
            headers=headers,
            accept='application/json',
        )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise HTTPRequestError(
                url=url,
                reason='invalid_json',
                status_code=response.status_code,
            ) from exc

    def post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        *,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        response = self.fetch_response(
            url,
            method='POST',
            timeout=timeout,
            headers=headers,
            accept='application/json',
            json_body=payload,
        )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise HTTPRequestError(
                url=url,
                reason='invalid_json',
                status_code=response.status_code,
            ) from exc

    def fetch_html(
        self,
        url: str,
        *,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        response = self.fetch_response(
            url,
            timeout=timeout,
            headers=headers,
            accept='text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        )
        return response.text

    def fetch_response(
        self,
        url: str,
        *,
        method: str = 'GET',
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        accept: Optional[str] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Response:
        request_headers = dict(headers or {})
        if accept:
            request_headers.setdefault('Accept', accept)
        if json_body is not None:
            request_headers.setdefault('Content-Type', 'application/json')

        timeout = timeout or self.config.request_timeout_seconds
        start = time.perf_counter()
        try:
            response = self.session.request(
                method,
                url,
                headers=request_headers,
                timeout=timeout,
                json=json_body,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.logger.info(
                'http_request method=%s url=%s status=%s elapsed_ms=%.1f',
                method,
                url,
                response.status_code,
                elapsed_ms,
            )
        except requests.RequestException as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.logger.warning(
                'http_request_failed method=%s url=%s elapsed_ms=%.1f error=%s',
                method,
                url,
                elapsed_ms,
                exc,
            )
            raise HTTPRequestError(url=url, reason='request_failed') from exc

        if response.status_code >= 400:
            raise HTTPRequestError(url=url, reason='bad_status', status_code=response.status_code)
        return response
