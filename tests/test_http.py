from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from crypto_report.config import ScriptConfig
from crypto_report.http_client import HTTPClient, HTTPRequestError
from crypto_report.logging_utils import configure_logging, get_logger


class HTTPClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ScriptConfig(generate_screenshots=False)
        configure_logging(self.config)
        self.client = HTTPClient(self.config, get_logger(__name__))

    def test_fetch_json_raises_for_invalid_payload(self) -> None:
        response = Mock(status_code=200)
        response.json.side_effect = json.JSONDecodeError('bad', 'x', 0)
        self.client.fetch_response = Mock(return_value=response)
        with self.assertRaises(HTTPRequestError):
            self.client.fetch_json('https://example.com')


if __name__ == "__main__":
    unittest.main()
