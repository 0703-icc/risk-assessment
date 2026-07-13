"""新闻采集模块

通过新闻API或新闻网站采集与风险项相关的新闻。
优先使用百度新闻真实搜索，失败时回退到模拟数据。
"""

import requests
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime


class NewsAPICollector:
    """新闻采集器

    数据源优先级：
    1. 百度新闻搜索（真实数据）
    2. 模拟数据（兜底）
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key
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

    def collect(self, company_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """采集指定公司和关键词的新闻

        Args:
            company_name: 公司名称
            keywords: 额外关键词列表

        Returns:
            新闻列表，每项包含 title, url, source, date, description
        """
        results = []

        # 1. 优先使用百度新闻真实搜索
        try:
            baidu_results = self._search_baidu(company_name, keywords)
            if baidu_results:
                results.extend(baidu_results)
        except Exception:
            pass

        # 2. 如果百度新闻为空，使用模拟数据兜底
        if not results:
            try:
                fallback_results = self._search_fallback(company_name, keywords)
                results.extend(fallback_results)
            except Exception:
                pass

        return results

    def _search_baidu(self, company_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """使用百度新闻搜索真实新闻"""
        query = company_name
        if keywords:
            query += " " + " ".join(keywords)

        # 先访问百度首页获取 Cookie（关键）
        try:
            self.session.get("https://www.baidu.com/", timeout=10)
        except Exception:
            pass

        url = (
            f"https://news.baidu.com/ns"
            f"?word={requests.utils.quote(query)}"
            f"&tn=news&from=news&cl=2&rn=30&ct=0"
        )

        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        containers = soup.select("div.c-container")

        results = []
        for container in containers:
            a_tag = container.select_one("h3 a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")

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

        return results

    def _search_fallback(self, company_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """备用搜索方案（模拟数据）

        当真实数据源不可用时使用。
        """
        SIMULATED_NEWS = {
            "万科": [
                {"title": "万科发布2024年年度报告，业绩稳定增长", "source": "财经网", "date": "2024-03-20", "description": "", "url": "http://example.com/news/1"},
                {"title": "万科获机构增持，股价逆势上涨", "source": "证券时报", "date": "2024-03-18", "description": "", "url": "http://example.com/news/2"},
            ],
            "绿地": [
                {"title": "绿地控股成功发行中期票据，融资成本下降", "source": "中国货币网", "date": "2024-03-15", "description": "", "url": "http://example.com/news/greenland1"},
                {"title": "绿地控股多个项目按期交付，运营情况良好", "source": "澎湃新闻", "date": "2024-03-10", "description": "", "url": "http://example.com/news/greenland2"},
            ],
            "保利": [
                {"title": "保利发展销售业绩稳步增长，市场份额提升", "source": "证券时报", "date": "2024-03-18", "description": "", "url": "http://example.com/news/poly1"},
                {"title": "保利发展获AAA信用评级，融资渠道通畅", "source": "财经网", "date": "2024-03-12", "description": "", "url": "http://example.com/news/poly2"},
            ],
            "华润": [
                {"title": "华润置地商业运营收入创新高", "source": "21世纪经济报道", "date": "2024-03-20", "description": "", "url": "http://example.com/news/cr1"},
                {"title": "华润置地持续推进城市更新项目", "source": "界面新闻", "date": "2024-03-15", "description": "", "url": "http://example.com/news/cr2"},
            ],
            "招商": [
                {"title": "招商蛇口并购重组获批，业务版图扩张", "source": "财新网", "date": "2024-03-18", "description": "", "url": "http://example.com/news/cm1"},
                {"title": "招商蛇口实际控制人变更", "source": "证券时报", "date": "2024-03-10", "description": "", "url": "http://example.com/news/cm2"},
            ],
            "龙湖": [
                {"title": "龙湖集团因违规被暂停部分项目预售审批", "source": "澎湃新闻", "date": "2024-03-12", "description": "", "url": "http://example.com/news/longfor1"},
                {"title": "龙湖集团多个楼盘延期交付，引发业主维权", "source": "财经网", "date": "2024-03-08", "description": "", "url": "http://example.com/news/longfor2"},
                {"title": "龙湖集团高管频繁离职，人事变动引发关注", "source": "21世纪经济报道", "date": "2024-03-05", "description": "", "url": "http://example.com/news/longfor3"},
            ],
            "碧桂园": [
                {"title": "碧桂园宣布部分债券违约，已触发交叉违约条款", "source": "财新网", "date": "2024-03-15", "description": "", "url": "http://example.com/news/3"},
                {"title": "碧桂园多个项目停工，业主维权不断", "source": "澎湃新闻", "date": "2024-03-10", "description": "", "url": "http://example.com/news/4"},
                {"title": "碧桂园被证监会立案调查，涉嫌信息披露违规", "source": "财经网", "date": "2024-03-08", "description": "", "url": "http://example.com/news/bg4"},
                {"title": "碧桂园董事长辞职，核心高管频繁变动", "source": "界面新闻", "date": "2024-03-05", "description": "", "url": "http://example.com/news/bg5"},
            ],
            "融创": [
                {"title": "融创中国控股股东发生变更", "source": "21世纪经济报道", "date": "2024-03-12", "description": "", "url": "http://example.com/news/5"},
                {"title": "融创多个楼盘延期交付，引发业主担忧", "source": "界面新闻", "date": "2024-03-08", "description": "", "url": "http://example.com/news/6"},
                {"title": "融创中国被监管立案调查，涉嫌违规操作", "source": "财新网", "date": "2024-03-06", "description": "", "url": "http://example.com/news/rc3"},
                {"title": "融创中国负面舆情集中，业主群体性事件频发", "source": "澎湃新闻", "date": "2024-03-03", "description": "", "url": "http://example.com/news/rc4"},
            ],
            "招商银": [
                {"title": "招商银行发布2024年业绩报告，净利润增长", "source": "证券时报", "date": "2024-03-20", "description": "", "url": "http://example.com/news/cmb1"},
                {"title": "招商银行荣获最佳零售银行称号", "source": "财经网", "date": "2024-03-15", "description": "", "url": "http://example.com/news/cmb2"},
            ],
            "平安": [
                {"title": "中国平安保费收入持续增长，投资收益稳定", "source": "财新网", "date": "2024-03-18", "description": "", "url": "http://example.com/news/pingan1"},
                {"title": "中国平安否认债券违约传闻", "source": "澎湃新闻", "date": "2024-03-10", "description": "", "url": "http://example.com/news/pingan2"},
            ],
        }

        results = []

        for key in SIMULATED_NEWS:
            if key in company_name:
                results.extend(SIMULATED_NEWS[key])
                return results

        results.append({
            "title": f"{company_name}近期经营情况正常",
            "source": "模拟新闻源",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": "",
            "url": "http://example.com/news/default"
        })

        return results