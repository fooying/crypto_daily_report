import unittest

try:
    from crypto_report.generator import CryptoReportGenerator
except Exception:  # pragma: no cover
    CryptoReportGenerator = None


class RenderSmokeTests(unittest.TestCase):
    def test_generate_html_report(self):
        if CryptoReportGenerator is None:
            self.skipTest("generator import failed")
        generator = CryptoReportGenerator()
        generator.market_overview = {"total_market_cap": 0, "total_volume": 0, "active_cryptocurrencies": 0, "market_cap_percentage": {}, "market_cap_change_percentage_24h_usd": 0}
        generator.fear_greed_index = {"value": 50, "classification": "Neutral"}
        generator.sentiment = generator.get_sentiment_analysis()
        generator.crypto_news = []
        generator.top_cryptos = []
        generator.market_cap_history = []
        generator.technical_context = {}
        try:
            html = generator.generate_html_report()
        except RuntimeError as exc:
            if "Jinja2" in str(exc):
                self.skipTest("jinja2 not installed")
            raise
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn(generator.config.report_title, html)


if __name__ == "__main__":
    unittest.main()
