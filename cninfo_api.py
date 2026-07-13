"""巨潮资讯网数据源

通过巨潮资讯网(cninfo.com.cn)查询上市公司公告。
支持按公司代码查询各类公告（年报、股权变动、处罚等）。
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',
}


class CNInfoCollector:
    """巨潮资讯采集器"""

    SEARCH_URL = 'http://www.cninfo.com.cn/new/information/topSearch/query'
    ANNOUNCE_URL = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _search_company(self, keyword: str) -> Optional[Dict[str, str]]:
        """搜索公司，返回 {code, orgId, name, plate, column}"""
        try:
            resp = self.session.post(
                self.SEARCH_URL,
                data={'keyWord': keyword, 'maxNum': 10},
                timeout=30
            )
            data = resp.json()
            if not data:
                return None
            # 返回第一个匹配项
            item = data[0]
            return {
                'code': item.get('code', ''),
                'orgId': item.get('orgId', ''),
                'name': item.get('zwjc', ''),
                'plate': item.get('plate', ''),      # sz/sh/bj
                'column': item.get('column', ''),    # szse/sse/bse
            }
        except Exception:
            return None

    def collect(self, company_name: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """采集指定公司的公告列表

        Args:
            company_name: 公司名称或股票代码
            start_date: 开始日期，格式 YYYY-MM-DD，默认一年前
            end_date: 结束日期，格式 YYYY-MM-DD，默认今天

        Returns:
            公告列表，每项包含 title, url, source, date, announcementType
        """
        # 日期默认值
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        # 1. 搜索公司信息
        company = self._search_company(company_name)
        if not company or not company.get('code'):
            return []

        code = company['code']
        org_id = company['orgId']
        column = company.get('column', 'szse')
        plate = company.get('plate', 'sz')

        # 2. 查询公告列表
        results = []
        try:
            resp = self.session.post(
                self.ANNOUNCE_URL,
                data={
                    'stock': f'{code},{org_id}',
                    'tabName': 'fulltext',
                    'pageSize': 50,
                    'pageNum': 1,
                    'column': column,
                    'plate': plate,
                    'seDate': f'{start_date}~{end_date}',
                },
                timeout=30
            )
            data = resp.json()

            announcements = data.get('announcements', []) or []
            for ann in announcements:
                title = ann.get('announcementTitle', '')
                adjunct_url = ann.get('adjunctUrl', '')
                pdf_url = f'http://static.cninfo.com.cn/{adjunct_url}' if adjunct_url else ''

                # 毫秒时间戳转日期
                ts = ann.get('announcementTime', 0)
                date_str = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d') if ts else ''

                results.append({
                    'title': title,
                    'url': pdf_url,
                    'source': '巨潮资讯',
                    'date': date_str,
                    'description': '',
                    'announcementType': ann.get('announcementType', ''),
                })

        except Exception:
            pass

        return results


# 公告类型映射（用于快速筛选）
ANNOUNCEMENT_TYPE_MAP = {
    'category_ndbg_szsh': '年度报告',
    'category_bndbg_szsh': '半年度报告',
    'category_yjdbg_szsh': '一季度报告',
    'category_sjdbg_szsh': '三季度报告',
    'category_gqbd_szsh': '股权变动',
    'category_dshgg_szsh': '董事会公告',
    'category_jshgg_szsh': '监事会公告',
    'category_gddh_szsh': '股东大会',
    'category_zj_szsh': '重大事项',
    'category_cg_szsh': '处罚/整改',
}
