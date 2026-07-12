"""数据采集模块

协调多个数据源采集器，获取公司相关的原始数据。
"""

from typing import Dict, List, Any

from datasources.news_api import NewsAPICollector
from datasources.bond_market import BondMarketCollector
from datasources.court_info import CourtInfoCollector


class DataCollector:
    """数据采集器主类"""

    def __init__(self):
        self.collectors = {
            "news_api": NewsAPICollector(),
            "bond_market": BondMarketCollector(),
            "court_info": CourtInfoCollector(),
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

        return results
