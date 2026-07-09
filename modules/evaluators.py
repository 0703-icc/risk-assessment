"""风险项评估引擎

根据采集的原始数据，判断各风险项的触发状态。
"""

from typing import List, Dict, Any
from config import RISK_ITEMS


class IndependentEvaluator:
    """独立项评估器

    独立项是二元事件，判断依据是原始数据中是否包含相关关键词。
    """

    # 否定关键词，用于检测信息冲突
    # 格式: (否定词, 需要紧跟的关键词列表) — 表示"否定词+关键词"构成否定
    NEGATION_PATTERNS = [
        ("未", None),           # "未"后面跟任何风险关键词都算否定
        ("不", None),           # "不"后面跟任何风险关键词都算否定
        ("无", None),           # "无"后面跟任何风险关键词都算否定
        ("没有", None),         # "没有"后面跟任何风险关键词都算否定
        ("否认", None),         # "否认"本身就是否定
        ("澄清", None),         # "澄清"本身就是否定
        ("辟谣", None),         # "辟谣"本身就是否定
    ]

    def _has_negation(self, text: str, risk_keywords: List[str]) -> bool:
        """检查文本中是否包含对风险关键词的否定

        规则：
        1. 如果否定词后面紧跟风险关键词 → 是否定（如"未违约""不兑付"）
        2. 如果否定词是独立完整的词（如"否认""澄清""辟谣"）→ 是否定
        3. 如果否定词只是其他词的一部分（如"不断""不是"）→ 不是否定
        """
        import re

        for neg, _ in self.NEGATION_PATTERNS:
            if neg not in text:
                continue

            # 模式1: 否定词是独立词（否认、澄清、辟谣）
            if neg in ["否认", "澄清", "辟谣"]:
                return True

            # 模式2: 否定词+风险关键词（如"未违约""不兑付"）
            for risk_kw in risk_keywords:
                # 检查否定词是否在风险关键词之前不远处
                combined = neg + risk_kw
                if combined in text:
                    return True

                # 检查否定词和风险关键词之间只有少量字符（最多10个字符）
                pattern = re.escape(neg) + r'.{0,10}' + re.escape(risk_kw)
                if re.search(pattern, text):
                    return True

        return False

    def evaluate(self, item_code: str, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估独立项

        Args:
            item_code: 风险项编码（如 I-001）
            raw_data: 采集的原始数据列表

        Returns:
            评估结果字典，包含 status, severity, evidence 等
        """
        item_config = RISK_ITEMS.get(item_code)
        if not item_config:
            return {"status": "数据不足", "message": "未知的风险项编码"}

        keywords = item_config.get("keywords", [])
        severity = item_config.get("severity")

        # 筛选包含关键词的数据
        matched = []
        negated = []

        for data in raw_data:
            title = data.get("title", "")
            content = data.get("description", "") or data.get("raw_content", "")
            text = title + " " + content

            # 检查是否包含风险关键词
            if any(kw in text for kw in keywords):
                # 检查是否包含对风险关键词的否定
                if self._has_negation(text, keywords):
                    negated.append(data)
                else:
                    matched.append(data)

        # 判断状态
        if matched and negated:
            status = "信息冲突"
        elif matched:
            status = "已触发"
        elif negated:
            status = "信息冲突"
        elif raw_data:
            status = "未触发"
        else:
            status = "数据不足"

        return {
            "status": status,
            "severity": severity,
            "evidence": matched,
            "conflicting_evidence": negated,
            "item_name": item_config["name"],
            "item_type": item_config["type"]
        }


class ReferenceEvaluator:
    """参考项评估器

    参考项需要参照基准判断是否异常。
    当前实现基于关键词匹配，后续可扩展为更复杂的判断逻辑。
    """

    def evaluate(self, item_code: str, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估参考项

        Args:
            item_code: 风险项编码（如 R-003）
            raw_data: 采集的原始数据列表

        Returns:
            评估结果字典，包含 status, evidence 等
        """
        item_config = RISK_ITEMS.get(item_code)
        if not item_config:
            return {"status": "数据不足", "message": "未知的风险项编码"}

        keywords = item_config.get("keywords", [])

        # 筛选包含关键词的数据
        matched = []
        for data in raw_data:
            title = data.get("title", "")
            content = data.get("description", "") or data.get("raw_content", "")
            text = title + " " + content

            if any(kw in text for kw in keywords):
                matched.append(data)

        # 判断状态
        if matched:
            status = "异常"
        elif raw_data:
            status = "正常"
        else:
            status = "数据不足"

        return {
            "status": status,
            "evidence": matched,
            "item_name": item_config["name"],
            "item_type": item_config["type"]
        }