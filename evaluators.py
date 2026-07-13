"""风险项评估引擎

根据采集的原始数据，判断各风险项的触发状态。

评估逻辑：
- 独立项：二元事件，发生即触发
- 参考项：量化分级，根据匹配数据量判断异常程度
"""

from typing import List, Dict, Any
from config import RISK_ITEMS


class IndependentEvaluator:
    """独立项评估器

    独立项是二元事件，判断依据是原始数据中是否包含相关关键词。
    """

    NEGATION_PATTERNS = [
        ("未", None),
        ("不", None),
        ("无", None),
        ("没有", None),
        ("否认", None),
        ("澄清", None),
        ("辟谣", None),
    ]

    def _has_negation(self, text: str, risk_keywords: List[str]) -> bool:
        """检查文本中是否包含对风险关键词的否定"""
        import re

        for neg, _ in self.NEGATION_PATTERNS:
            if neg not in text:
                continue

            if neg in ["否认", "澄清", "辟谣"]:
                return True

            for risk_kw in risk_keywords:
                combined = neg + risk_kw
                if combined in text:
                    return True

                pattern = re.escape(neg) + r'.{0,10}' + re.escape(risk_kw)
                if re.search(pattern, text):
                    return True

        return False

    def evaluate(self, item_code: str, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估独立项"""
        item_config = RISK_ITEMS.get(item_code)
        if not item_config:
            return {"status": "数据不足", "message": "未知的风险项编码"}

        keywords = item_config.get("keywords", [])
        severity = item_config.get("severity")

        matched = []
        negated = []

        for data in raw_data:
            title = data.get("title", "")
            content = data.get("description", "") or data.get("raw_content", "")
            text = title + " " + content

            if any(kw in text for kw in keywords):
                if self._has_negation(text, keywords):
                    negated.append(data)
                else:
                    matched.append(data)

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
            "item_type": item_config["type"],
            "match_count": len(matched),
            "total_data": len(raw_data),
        }


class ReferenceEvaluator:
    """参考项评估器

    参考项需要参照基准判断是否异常。
    当前实现基于关键词匹配的量化分级：
    - 0条：正常
    - 1条：轻度关注
    - 2-3条：中度异常
    - 4条以上：严重异常

    后续可扩展为基于历史均值/行业均值的真正参照系对比。
    """

    # 量化分级阈值
    THRESHOLDS = {
        "正常": (0, 0),
        "轻度关注": (1, 1),
        "中度异常": (2, 3),
        "严重异常": (4, float('inf')),
    }

    def _classify(self, match_count: int) -> str:
        """根据匹配数量分级"""
        if match_count == 0:
            return "正常"
        elif match_count == 1:
            return "轻度关注"
        elif 2 <= match_count <= 3:
            return "中度异常"
        else:
            return "严重异常"

    def evaluate(self, item_code: str, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估参考项

        Returns:
            包含 status, evidence, match_count, total_data, level 等的字典
        """
        item_config = RISK_ITEMS.get(item_code)
        if not item_config:
            return {"status": "数据不足", "message": "未知的风险项编码"}

        keywords = item_config.get("keywords", [])

        matched = []
        for data in raw_data:
            title = data.get("title", "")
            content = data.get("description", "") or data.get("raw_content", "")
            text = title + " " + content

            if any(kw in text for kw in keywords):
                matched.append(data)

        match_count = len(matched)
        total_data = len(raw_data)

        # 判断状态
        if total_data == 0:
            status = "数据不足"
        else:
            status = self._classify(match_count)

        return {
            "status": status,
            "evidence": matched,
            "item_name": item_config["name"],
            "item_type": item_config["type"],
            "match_count": match_count,
            "total_data": total_data,
            "level": status,
        }
