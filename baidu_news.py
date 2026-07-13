"""百度新闻搜索数据源

通过百度新闻搜索获取与公司相关的真实新闻。
"""

import requests
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any


class BaiduNewsCollector:
    """百度新闻采集器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        # 先访问百度首页获取 Cookie（关键步骤）
        try:
            self.session.get("https://www.baidu.com/", timeout=15)
        except Exception:
            pass

    def collect(self, company_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """采集指定公司和关键词的百度新闻

        Args:
            company_name: 公司名称
            keywords: 额外关键词列表

        Returns:
            新闻列表，每项包含 title, url, source, date, description
        """
        query = company_name
        if keywords:
            query += " " + " ".join(keywords)

        url = (
            f"https://news.baidu.com/ns"
            f"?word={requests.utils.quote(query)}"
            f"&tn=news&from=news&cl=2&rn=30&ct=0"
        )

        results = []
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            containers = soup.select("div.c-container")

            for container in containers:
                a_tag = container.select_one("h3 a")
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                href = a_tag.get("href", "")

                # 从 HTML 注释里的 JSON 提取摘要/来源/时间
                abstract = ""
                source_name = "百度新闻"
                pub_time = ""

                comment = container.find(
                    string=lambda t: isinstance(t, str) and t.startswith("<!--s-data:")
                )
                if comment:
                    try:
                        json_str = comment.replace("<!--s-data:", "").replace("-->", "").strip()
                        comment_data = json.loads(json_str)
                        abstract = comment_data.get("summary", "")
                        source_name = comment_data.get("sourceName", "百度新闻")
                        pub_time = comment_data.get("dispTime", "")
                    except Exception:
                        pass

                results.append({
                    "title": title,
                    "url": href,
                    "source": source_name,
                    "date": pub_time,
                    "description": abstract,
                })

        except Exception:
            pass

        return results
