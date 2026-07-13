"""数据采集模块

协调多个数据源采集器，获取公司相关的原始数据。
"""

from typing import Dict, List, Any

from datasources.news_api import NewsAPICollector
from datasources.bond_market import BondMarketCollector
from datasources.court_info import CourtInfoCollector
from cninfo_api import CNInfoCollector


class DataCollector:
    """数据采集器主类"""

    def __init__(self):
        self.collectors = {
            "news_api": NewsAPICollector(),
            "bond_market": BondMarketCollector(),
            "court_info": CourtInfoCollector(),
            "cninfo": CNInfoCollector(),
            "government": None,
        }

    def collect(self, company_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """采集所有数据源的数据

        Args:
            company_name: 公司名称

        Returns:
            各数据源的数据字典
        """
        results = {}

        for source_name, collector in self.collectors.items():
            if collector is None:
                results[source_name] = []
                continue

            try:
                data = collector.collect(company_name)
                results[source_name] = data
            except Exception:
                results[source_name] = []

        # 将巨潮资讯的公告也合并到 news_api 中，供评估器统一使用
        # 这样独立项和参考项的评估可以同时看到公告和新闻
        if results.get("cninfo") and results.get("news_api") is not None:
            results["news_api"].extend(results["cninfo"])

        return results
