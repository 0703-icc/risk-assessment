"""数据采集框架主模块

统一调度各数据源采集器，汇总采集结果。
"""

import logging
from typing import Dict, List, Any

from datasources.court_info import CourtInfoCollector
from datasources.news_api import NewsAPICollector
from datasources.bond_market import BondMarketCollector
from config import RISK_ITEMS

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集主类

    协调多个数据源采集器，并行采集目标公司的风险相关信息。
    """

    def __init__(self, news_api_key: str = None):
        self.collectors = {
            "court_info": CourtInfoCollector(),
            "news_api": NewsAPICollector(api_key=news_api_key),
            "bond_market": BondMarketCollector(),
        }

    def collect(self, company_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """采集指定公司的所有数据源信息

        Args:
            company_name: 目标公司名称

        Returns:
            按数据源分类的采集结果字典
        """
        results = {
            "court_info": [],
            "news_api": [],
            "bond_market": [],
        }

        # 采集司法信息
        try:
            results["court_info"] = self.collectors["court_info"].collect(company_name)
        except Exception as e:
            logger.warning(f"司法信息采集失败: {e}")
            results["court_info"] = []

        # 采集新闻信息（合并所有风险项的关键词）
        try:
            all_keywords = set()
            for item in RISK_ITEMS.values():
                all_keywords.update(item.get("keywords", []))

            results["news_api"] = self.collectors["news_api"].collect(
                company_name,
                keywords=list(all_keywords)
            )
        except Exception as e:
            logger.warning(f"新闻采集失败: {e}")
            results["news_api"] = []

        # 采集债券市场信息
        try:
            results["bond_market"] = self.collectors["bond_market"].collect(company_name)
        except Exception as e:
            logger.warning(f"债券信息采集失败: {e}")
            results["bond_market"] = []

        return results