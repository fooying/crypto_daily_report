from __future__ import annotations

import datetime
import re
from datetime import datetime as dt, timedelta
from typing import Any, Dict, List, Tuple

from ..config import BACKUP_NEWS_URL, PRIMARY_NEWS_BASE_URL, PRIMARY_NEWS_URL
from ..http_client import HTTPRequestError
from ..models import NewsItem

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


class NewsService:
    """Fetch and parse upstream news pages with parser helpers suitable for fixtures."""

    def __init__(self, config, http, logger, now_provider=None) -> None:
        self.config = config
        self.http = http
        self.logger = logger
        self.now_provider = now_provider or dt.now
        self.news_date_range = "最新"
        self.last_source_used = "unknown"

    def parse_news_time(self, time_text: str, now: dt, fallback_time: dt) -> dt:
        if not time_text:
            return fallback_time
        try:
            if "小时前" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    return now - datetime.timedelta(hours=int(match.group(1)))
            elif "天前" in time_text:
                match = re.search(r"(\d+)", time_text)
                if match:
                    return now - datetime.timedelta(days=int(match.group(1)))
            else:
                return dt.strptime(time_text, "%Y-%m-%d %H:%M")
        except Exception:
            return fallback_time
        return fallback_time

    @staticmethod
    def _normalize_news_key(item: NewsItem) -> tuple[str, str]:
        title = re.sub(r"\s+", " ", str(item.get("title", "")).strip().lower())
        url = str(item.get("url", "")).strip().lower()
        return title, url

    def deduplicate_news(self, items: List[NewsItem]) -> List[NewsItem]:
        unique_items: List[NewsItem] = []
        seen_keys = set()
        for item in items:
            key = self._normalize_news_key(item)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique_items.append(item)
        return unique_items

    def classify_news_sentiment(self, title: str, summary: str) -> str:
        positive_keywords = [
            "涨", "上涨", "突破", "创新高", "利好", "增长", "复苏", "反弹", "盈利", "收益",
            "成功", "批准", "通过", "合作", "投资", "扩张", "发展", "升级", "优化", "积极", "正面",
        ]
        negative_keywords = [
            "跌", "下跌", "暴跌", "下滑", "亏损", "损失", "失败", "拒绝", "崩盘", "危机", "风险",
            "警告", "担忧", "调查", "罚款", "诉讼", "违规", "欺诈", "黑客", "攻击", "漏洞", "利空",
        ]
        neutral_themes = ["监管", "政策", "法律", "合规", "标准", "框架", "讨论", "会议"]
        text_to_check = (title + " " + summary).lower()
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_to_check)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_to_check)
        if positive_count > negative_count:
            return "积极"
        if negative_count > positive_count:
            return "谨慎"
        if any(theme in text_to_check for theme in neutral_themes):
            return "中性"
        if "投资" in text_to_check or "合作" in text_to_check:
            return "积极"
        if "罚款" in text_to_check or "调查" in text_to_check:
            return "谨慎"
        return "中性"

    def classify_news_tags(self, title: str, summary: str) -> List[str]:
        text_to_check = (title + " " + summary).lower()
        tag_rules = [
            ("监管", ["监管", "政策", "合规", "批准", "牌照", "诉讼", "审查"]),
            ("ETF/机构", ["etf", "机构", "基金", "银行", "上市公司", "财库"]),
            ("安全事件", ["黑客", "攻击", "漏洞", "盗", "安全事件", "风险事件"]),
            ("DeFi", ["defi", "借贷", "tvl", "流动性", "协议"]),
            ("交易所", ["coinbase", "binance", "bybit", "交易所", "上币"]),
            ("链上/挖矿", ["矿工", "链上", "地址", "储备", "哈希"]),
            ("技术升级", ["升级", "主网", "layer2", "zk", "rollup", "测试网"]),
        ]
        tags = [label for label, keywords in tag_rules if any(keyword in text_to_check for keyword in keywords)]
        return tags[:3]

    def classify_news_impact(self, title: str, summary: str, tags: List[str] | None = None) -> str:
        text_to_check = (title + " " + summary).lower()
        tag_set = set(tags or [])
        high_priority_tags = {"监管", "ETF/机构", "安全事件"}
        medium_priority_tags = {"交易所", "技术升级", "DeFi", "链上/挖矿"}
        if tag_set & high_priority_tags:
            return "高影响"
        if any(keyword in text_to_check for keyword in ["etf", "黑客", "监管", "批准", "诉讼", "攻击"]):
            return "高影响"
        if tag_set & medium_priority_tags:
            return "中影响"
        if any(keyword in text_to_check for keyword in ["升级", "主网", "交易所", "defi", "矿工"]):
            return "中影响"
        return "一般"

    def extract_news_summary(
        self,
        article: Any,
        fallback_title: str,
        link: str,
        listing_url: str,
        headers: Dict[str, str],
        detail_fetch_count: int,
    ) -> Tuple[str, int]:
        if BeautifulSoup is None:
            return fallback_title[:150], detail_fetch_count

        summary = "点击查看详情"
        summary_elem = article.find("p", class_=re.compile(r"summary|excerpt|description|post-card__text|post-card-inline__text"))
        if summary_elem:
            summary = summary_elem.get_text(strip=True)

        if (
            summary == "点击查看详情"
            and link != listing_url
            and detail_fetch_count < self.config.max_news_detail_fetches
        ):
            try:
                article_html = self.http.fetch_html(
                    link,
                    timeout=self.config.article_request_timeout_seconds,
                    headers=headers,
                )
                detail_fetch_count += 1
                article_soup = BeautifulSoup(article_html, "html.parser")
                content_elem = article_soup.find(
                    "div", class_=re.compile(r"post-content|article-content|content")
                )
                if content_elem:
                    first_para = content_elem.find("p")
                    if first_para:
                        summary = first_para.get_text(strip=True)[:200]
                else:
                    for selector in ["article p", ".post p", ".article p"]:
                        paras = article_soup.select(selector)
                        if paras:
                            summary = paras[0].get_text(strip=True)[:200]
                            break
            except Exception as exc:
                self.logger.debug(f"访问新闻详情页失败: {exc}")

        if summary == "点击查看详情":
            summary = fallback_title[:150]
        return summary, detail_fetch_count

    def parse_primary_news_html(self, html: str, listing_url: str | None = None) -> List[NewsItem]:
        if BeautifulSoup is None:
            return []

        listing_url = listing_url or PRIMARY_NEWS_URL
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all("article", class_=re.compile(r"post-card|post-card-inline"))
        if not articles:
            articles = soup.find_all("div", class_=re.compile(r"post-card|article-card"))

        today = self.now_provider()
        if today.weekday() == 0:
            start_date = today - timedelta(days=3)
            date_range_text = f"{start_date.strftime('%m月%d日')}-{today.strftime('%m月%d日')}"
        else:
            start_date = today - timedelta(days=1)
            date_range_text = f"{start_date.strftime('%m月%d日')}"
        self.news_date_range = date_range_text

        news_items: List[NewsItem] = []
        detail_fetch_count = 0
        for article in articles[: self.config.max_news_analysis_items]:
            try:
                title_elem = article.find(["h2", "h3", "h4", "span"], class_=re.compile(r"title|headline"))
                if not title_elem:
                    title_elem = article.find("a", class_=re.compile(r"title"))
                title = title_elem.get_text(strip=True) if title_elem else "未找到标题"

                link_elem = article.find("a", href=True)
                link = link_elem["href"] if link_elem else listing_url
                if link.startswith("/"):
                    link = f"{PRIMARY_NEWS_BASE_URL}{link}"

                summary, detail_fetch_count = self.extract_news_summary(
                    article=article,
                    fallback_title=title,
                    link=link,
                    listing_url=listing_url,
                    headers=headers,
                    detail_fetch_count=detail_fetch_count,
                )

                time_elem = article.find("time")
                news_time = start_date
                if time_elem:
                    news_time = self.parse_news_time(time_elem.get_text(strip=True), today, start_date)

                if news_time.date() >= start_date.date():
                    tags = self.classify_news_tags(title, summary)
                    news_items.append(
                        {
                            "title": title,
                            "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                            "sentiment": self.classify_news_sentiment(title, summary),
                            "impact": self.classify_news_impact(title, summary, tags),
                            "time": news_time.strftime("%Y-%m-%d %H:%M"),
                            "url": link,
                            "source": "CoinTelegraph",
                            "tags": tags,
                        }
                    )
            except Exception as exc:
                self.logger.warning(f"解析新闻文章失败: {exc}")
        return news_items

    def parse_backup_news_html(self, html: str) -> List[NewsItem]:
        if BeautifulSoup is None:
            return []

        soup = BeautifulSoup(html, "html.parser")
        news_items: List[NewsItem] = []
        articles = soup.find_all("a", href=lambda value: value and "/zh/news/" in value)
        for article in articles[: self.config.max_news_analysis_items]:
            title_elem = article.find(["h3", "h4"]) or article
            title = title_elem.get_text(strip=True)
            if title and len(title) > 10:
                tags = self.classify_news_tags(title, "")
                news_items.append(
                    {
                        "title": title[:80],
                        "summary": "点击查看详情",
                        "sentiment": "中性",
                        "impact": self.classify_news_impact(title, "", tags),
                        "time": "最新",
                        "source": "CoinMarketCap",
                        "url": f"https://coinmarketcap.com{article.get('href', '')}",
                        "tags": tags,
                    }
                )
        return news_items

    def get_backup_news(self) -> List[NewsItem]:
        try:
            url = BACKUP_NEWS_URL
            html = self.http.fetch_html(url, timeout=self.config.news_request_timeout_seconds)
            news_items = self.parse_backup_news_html(html)
            if news_items:
                self.last_source_used = "coinmarketcap_backup"
                self.logger.info("新闻数据已切换为 CoinMarketCap 备用源")
                return news_items
        except HTTPRequestError as exc:
            self.logger.warning("CoinMarketCap 备用新闻源请求失败: %s", exc)
        except Exception as exc:
            self.logger.warning("CoinMarketCap 备用新闻源获取失败: %s", exc)

        self.last_source_used = "fallback_stub"
        return []

    def get_crypto_news(self) -> List[NewsItem]:
        try:
            url = PRIMARY_NEWS_URL
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            html = self.http.fetch_html(
                url,
                timeout=self.config.news_request_timeout_seconds,
                headers=headers,
            )
            news_items = self.deduplicate_news(self.parse_primary_news_html(html, listing_url=url))
            self.last_source_used = "cointelegraph_primary"
            primary_count = len(news_items)
            backup_added = 0
            if len(news_items) < self.config.max_news_analysis_items:
                self.logger.warning(
                    "CoinTelegraph 主源仅获取 %s 条，低于目标 %s 条，尝试补充备用源",
                    len(news_items),
                    self.config.max_news_analysis_items,
                )
                backup_news = self.get_backup_news()[
                    : self.config.max_news_analysis_items - len(news_items)
                ]
                if backup_news:
                    before_merge_count = len(news_items)
                    news_items = self.deduplicate_news(news_items + backup_news)
                    backup_added = max(len(news_items) - before_merge_count, 0)
                    self.last_source_used = "mixed_primary_backup"
            self.logger.info(
                "成功获取 %s 条新闻，主源 %s 条，备用补充 %s 条，时间范围: %s",
                len(news_items),
                primary_count,
                backup_added,
                self.news_date_range,
            )
            return news_items[: self.config.max_news_analysis_items]
        except HTTPRequestError as exc:
            self.logger.warning("CoinTelegraph 新闻源请求失败，尝试 CoinMarketCap 备用源: %s", exc)
        except Exception as exc:
            self.logger.warning("CoinTelegraph 新闻源获取失败，尝试 CoinMarketCap 备用源: %s", exc)
            return self.get_backup_news()
        return self.get_backup_news()
