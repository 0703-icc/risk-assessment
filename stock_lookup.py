"""股票代码识别模块

通过公开接口将股票代码解析为公司名称。
支持 A 股、港股、美股等市场，以及统一社会信用代码查询。
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict


# 预置热门开发商映射（股票代码）
BUILTIN_COMPANIES = {
    "000002": {"name": "万科A", "market": "深A"},
    "600606": {"name": "绿地控股", "market": "沪A"},
    "600048": {"name": "保利发展", "market": "沪A"},
    "1109": {"name": "华润置地", "market": "港股"},
    "001979": {"name": "招商蛇口", "market": "深A"},
    "00960": {"name": "龙湖集团", "market": "港股"},
    "2007": {"name": "碧桂园", "market": "港股"},
    "1918": {"name": "融创中国", "market": "港股"},
    "600036": {"name": "招商银行", "market": "沪A"},
    "601318": {"name": "中国平安", "market": "沪A"},
}

# 预置统一社会信用代码映射（上市企业 + 非上市企业）
BUILTIN_CREDIT_CODES = {
    # 上市房地产企业
    "911100001011203558": {"name": "万科企业股份有限公司", "market": "深A", "stock": "000002"},
    "91310000631650488Y": {"name": "绿地控股集团股份有限公司", "market": "沪A", "stock": "600606"},
    "9144060672247309X9": {"name": "碧桂园控股有限公司", "market": "港股", "stock": "2007"},
    "914403001921843897": {"name": "招商局蛇口工业区控股股份有限公司", "market": "深A", "stock": "001979"},
    "91110000717824210R": {"name": "龙湖集团控股有限公司", "market": "港股", "stock": "00960"},
    "91310000132260326U": {"name": "融创中国控股有限公司", "market": "港股", "stock": "1918"},
    # 非上市/其他企业
    "91440300708461136K": {"name": "深圳市腾讯计算机系统有限公司", "market": "非上市"},
    "91110000MA01WJ7X9H": {"name": "北京字节跳动科技有限公司", "market": "非上市"},
    "91110000722601458H": {"name": "中国建筑股份有限公司", "market": "沪A", "stock": "601668"},
    "91110000710926094P": {"name": "中国中铁股份有限公司", "market": "沪A", "stock": "601390"},
    "911100001000238753": {"name": "北京城建投资发展股份有限公司", "market": "沪A", "stock": "600266"},
    "91110112802441203C": {"name": "北京城建集团有限责任公司", "market": "非上市"},
    "91110000710929580L": {"name": "保利发展控股集团股份有限公司", "market": "沪A", "stock": "600048"},
    "91110000100005362N": {"name": "华润置地控股有限公司", "market": "港股", "stock": "1109"},
}

# 本地缓存，避免重复请求
_code_cache: Dict[str, Optional[Dict[str, str]]] = {}


def _is_stock_code(input_text: str) -> bool:
    """判断输入是否像股票代码"""
    return bool(re.fullmatch(r"[A-Za-z0-9]{1,6}", input_text.strip()))


def _is_hk_code(code: str) -> bool:
    """判断是否为港股代码（1-5位数字，通常以0开头）"""
    return bool(re.fullmatch(r"0?\d{1,5}", code))


def _is_credit_code(input_text: str) -> bool:
    """判断是否为统一社会信用代码（18位，格式：91xxxxxxxxxxxxxxxxxx）"""
    pattern = r"^[0-9A-HJ-NP-RT-UW-Y]{2}[0-9]{6}[0-9A-HJ-NP-RT-UW-Y]{10}$"
    return bool(re.fullmatch(pattern, input_text.strip().upper()))


def lookup_stock_code(code: str, timeout: int = 10) -> Optional[Dict[str, str]]:
    """通过东方财富接口查询股票代码对应的公司名称

    Args:
        code: 股票代码，如 600606、000002、1109、AAPL
        timeout: 请求超时时间（秒）

    Returns:
        {"code": "600606", "name": "绿地控股", "market": "沪A"} 或 None
    """
    code = code.strip()
    if not _is_stock_code(code):
        return None

    if code in _code_cache:
        return _code_cache[code]

    try:
        url = "http://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": code,
            "type": "14",
            "count": "5",
        }
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        items = data.get("QuotationCodeTable", {}).get("Data", [])
        if not items:
            _code_cache[code] = None
            return None

        item = items[0]
        result = {
            "code": item.get("Code", code),
            "name": item.get("Name", "").strip(),
            "market": item.get("SecurityTypeName", ""),
        }

        if result["code"] != code and result["code"].lstrip("0") != code.lstrip("0"):
            _code_cache[code] = None
            return None

        _code_cache[code] = result
        return result

    except Exception:
        _code_cache[code] = None
        return None


def lookup_credit_code(credit_code: str, timeout: int = 10) -> Optional[Dict[str, str]]:
    """通过百度搜索查询统一社会信用代码对应的企业名称

    Args:
        credit_code: 统一社会信用代码（18位）
        timeout: 请求超时时间（秒）

    Returns:
        {"code": "91110000MA01WJ7X9H", "name": "企业名称", "market": "非上市"} 或 None
    """
    credit_code = credit_code.strip().upper()
    if not _is_credit_code(credit_code):
        return None

    if credit_code in _code_cache:
        return _code_cache[credit_code]

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        })
        session.get("https://www.baidu.com/", timeout=5)

        url = (
            f"https://www.baidu.com/s"
            f"?wd={requests.utils.quote(f'{credit_code} 企业名称')}"
            f"&pn=0"
        )
        response = session.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        result = None

        result_cards = soup.select("div.result-op.c-container.xpath-log.new-pmd")
        for card in result_cards:
            name_span = card.select_one("span.tfB0Bf")
            if name_span:
                company_name = name_span.get_text(strip=True)
                if company_name:
                    result = {
                        "code": credit_code,
                        "name": company_name,
                        "market": "非上市",
                    }
                    break

        if not result:
            title_tags = soup.select("h3.t")
            for title in title_tags[:5]:
                title_text = title.get_text(strip=True)
                if "统一社会信用代码" in title_text or credit_code[:8] in title_text:
                    company_name = title_text.replace("统一社会信用代码", "").replace(credit_code, "").strip()
                    if company_name and len(company_name) > 2:
                        result = {
                            "code": credit_code,
                            "name": company_name,
                            "market": "非上市",
                        }
                        break

        _code_cache[credit_code] = result
        return result

    except Exception:
        _code_cache[credit_code] = None
        return None


def resolve_company_name(input_text: str) -> Optional[Dict[str, str]]:
    """解析用户输入，尝试识别为股票代码或统一社会信用代码并返回公司信息

    优先级：
    1. 统一社会信用代码（先查预置映射，再尝试百度搜索）
    2. 预置映射（覆盖股票代码）
    3. 东方财富接口查询（A股、美股等）
    4. 港股代码特殊处理

    Args:
        input_text: 用户输入，可能是股票代码、简称、全称、统一社会信用代码

    Returns:
        {"code": "...", "name": "...", "market": "..."} 或 None
    """
    input_text = input_text.strip()
    if not input_text:
        return None

    # 1. 统一社会信用代码优先识别（18位）
    if _is_credit_code(input_text):
        credit_code = input_text.upper()
        if credit_code in BUILTIN_CREDIT_CODES:
            info = BUILTIN_CREDIT_CODES[credit_code]
            return {"code": credit_code, "name": info["name"], "market": info["market"]}

        result = lookup_credit_code(credit_code)
        if result:
            return result

    if not _is_stock_code(input_text):
        return None

    # 2. 先查预置映射
    if input_text in BUILTIN_COMPANIES:
        info = BUILTIN_COMPANIES[input_text]
        return {"code": input_text, "name": info["name"], "market": info["market"]}

    # 3. A股：优先用东方财富接口
    if re.fullmatch(r"\d{6}", input_text):
        result = lookup_stock_code(input_text)
        if result:
            return result

    # 4. 港股：尝试补零后查询
    if _is_hk_code(input_text):
        padded = input_text.zfill(5)
        if len(padded) <= 5:
            result = lookup_stock_code(padded)
            if result and result["market"] == "港股":
                return {"code": input_text, "name": result["name"], "market": "港股"}

    # 5. 美股/其他
    if re.fullmatch(r"[A-Za-z]{1,5}", input_text):
        result = lookup_stock_code(input_text.upper())
        if result:
            return result

    return None
