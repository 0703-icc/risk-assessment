"""股票代码识别模块

通过公开接口将股票代码解析为公司名称。
支持 A 股、港股、美股等市场。
"""

import re
import requests
from typing import Optional, Dict


# 预置热门开发商映射（港股/特殊代码）
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

# 本地缓存，避免重复请求
_code_cache: Dict[str, Optional[Dict[str, str]]] = {}


def _is_stock_code(input_text: str) -> bool:
    """判断输入是否像股票代码"""
    return bool(re.fullmatch(r"[A-Za-z0-9]{1,6}", input_text.strip()))


def _is_hk_code(code: str) -> bool:
    """判断是否为港股代码（1-5位数字，通常以0开头）"""
    return bool(re.fullmatch(r"0?\d{1,5}", code))


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

    # 先查缓存
    if code in _code_cache:
        return _code_cache[code]

    try:
        url = "http://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": code,
            "type": "14",  # 股票
            "count": "5",
        }
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        items = data.get("QuotationCodeTable", {}).get("Data", [])
        if not items:
            _code_cache[code] = None
            return None

        # 取第一个匹配项
        item = items[0]
        result = {
            "code": item.get("Code", code),
            "name": item.get("Name", "").strip(),
            "market": item.get("SecurityTypeName", ""),
        }

        # 如果返回的代码和输入不一致，可能是联想结果而非精确匹配
        if result["code"] != code and result["code"].lstrip("0") != code.lstrip("0"):
            _code_cache[code] = None
            return None

        _code_cache[code] = result
        return result

    except Exception:
        _code_cache[code] = None
        return None


def resolve_company_name(input_text: str) -> Optional[Dict[str, str]]:
    """解析用户输入，尝试识别为股票代码并返回公司信息

    优先级：
    1. 预置映射（覆盖港股等特殊代码）
    2. 东方财富接口查询（A股、美股等）
    3. 港股代码特殊处理

    Args:
        input_text: 用户输入，可能是股票代码、简称、全称

    Returns:
        {"code": "600606", "name": "绿地控股", "market": "沪A"} 或 None
    """
    input_text = input_text.strip()
    if not input_text:
        return None

    if not _is_stock_code(input_text):
        return None

    # 1. 先查预置映射
    if input_text in BUILTIN_COMPANIES:
        info = BUILTIN_COMPANIES[input_text]
        return {"code": input_text, "name": info["name"], "market": info["market"]}

    # 2. A股：优先用东方财富接口
    if re.fullmatch(r"\d{6}", input_text):
        result = lookup_stock_code(input_text)
        if result:
            return result

    # 3. 港股：尝试补零后查询
    if _is_hk_code(input_text):
        padded = input_text.zfill(5)
        # 港股以 0 开头且不超过 5 位
        if len(padded) <= 5:
            result = lookup_stock_code(padded)
            if result and result["market"] == "港股":
                return {"code": input_text, "name": result["name"], "market": "港股"}

    # 4. 美股/其他
    if re.fullmatch(r"[A-Za-z]{1,5}", input_text):
        result = lookup_stock_code(input_text.upper())
        if result:
            return result

    return None
