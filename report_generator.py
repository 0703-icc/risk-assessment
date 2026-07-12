"""报告生成器

生成在线报告和PDF导出。
"""

import io
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from database import get_latest_report, get_report_risk_items, init_db
from config import INDEPENDENT_ITEMS, REFERENCE_ITEMS


# 中文字体注册（跨平台兼容）
_CHINESE_FONT_REGISTERED = False
_CHINESE_FONT_NAME = "Helvetica"  # 默认回退

# 项目根目录（基于本文件位置向上一层）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 项目自带字体（最高优先级）+ 系统字体回退
_CANDIDATE_FONTS = [
    # 项目自带字体（确保跨平台一致）
    (os.path.join(_PROJECT_ROOT, "fonts", "SimHei.ttf"), 0),
    # Windows
    ("C:/Windows/Fonts/simhei.ttf", 0),
    # Linux (Streamlit Cloud / Debian)
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0),
    # macOS
    ("/System/Library/Fonts/PingFang.ttc", 0),
]


def _register_chinese_font():
    """注册中文字体，只需执行一次"""
    global _CHINESE_FONT_REGISTERED, _CHINESE_FONT_NAME
    if _CHINESE_FONT_REGISTERED:
        return

    for font_path, subfont_idx in _CANDIDATE_FONTS:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", font_path, subfontIndex=subfont_idx))
                _CHINESE_FONT_NAME = "ChineseFont"
                break
            except Exception:
                try:
                    # 某些 .ttc 文件需要指定 subfontIndex
                    pdfmetrics.registerFont(TTFont("ChineseFont", font_path, subfontIndex=0))
                    _CHINESE_FONT_NAME = "ChineseFont"
                    break
                except Exception:
                    continue

    _CHINESE_FONT_REGISTERED = True


class ReportGenerator:
    """报告生成器"""

    # 颜色定义
    COLOR_SEVERE = colors.HexColor("#FF4B4B")
    COLOR_WARNING = colors.HexColor("#FFD700")
    COLOR_GRAY = colors.HexColor("#808080")
    COLOR_GREEN = colors.HexColor("#4CAF50")

    def __init__(self, db_path: str = "data/risk_assessment.db"):
        self.db_path = db_path
        init_db(db_path)
        _register_chinese_font()

    def get_report_data(self, company_name: str) -> Optional[Dict[str, Any]]:
        """获取报告的完整数据（报告+风险项）"""
        report = get_latest_report(company_name, self.db_path)
        if not report:
            return None

        risk_items = get_report_risk_items(report["id"], self.db_path)

        # 分类和排序
        independent_items = []
        reference_items = []

        for item in risk_items:
            if item["item_type"] == "独立项":
                independent_items.append(item)
            else:
                reference_items.append(item)

        # 独立项按严重程度排序（严重在前）
        severity_order = {"严重": 0, "警示": 1, None: 2}
        independent_items.sort(key=lambda x: severity_order.get(x["severity"], 2))

        # 参考项按序号排序
        reference_items.sort(key=lambda x: x["item_code"])

        return {
            "report": dict(report),
            "independent_items": independent_items,
            "reference_items": reference_items
        }

    def generate_pdf(self, company_name: str) -> bytes:
        """生成PDF报告"""
        data = self.get_report_data(company_name)
        if not data:
            raise ValueError(f"未找到 {company_name} 的评估报告")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        font_name = _CHINESE_FONT_NAME

        # 自定义样式（全部使用中文字体）
        title_style = ParagraphStyle(
            'CustomTitle',
            fontName=font_name,
            fontSize=20,
            spaceAfter=30,
            alignment=1  # 居中
        )
        normal_style = ParagraphStyle(
            'ChineseNormal',
            fontName=font_name,
            fontSize=11,
            leading=18
        )
        heading_style = ParagraphStyle(
            'ChineseHeading',
            fontName=font_name,
            fontSize=14,
            spaceBefore=10,
            spaceAfter=10
        )

        # 报告标题
        elements.append(Paragraph("风险评估报告", title_style))
        elements.append(Spacer(1, 20))

        # 基本信息
        report = data["report"]
        elements.append(Paragraph(f"<b>开发商名称：</b>{report['company_name']}", normal_style))
        elements.append(Paragraph(f"<b>评估时间：</b>{report['evaluation_time']}", normal_style))
        elements.append(Spacer(1, 20))

        # 独立项
        elements.append(Paragraph("<b>独立项评估</b>", heading_style))
        elements.append(Spacer(1, 10))

        for item in data["independent_items"]:
            elements.append(self._create_item_paragraph(item, normal_style, font_name))
            elements.append(Spacer(1, 5))

        elements.append(Spacer(1, 20))

        # 参考项
        elements.append(Paragraph("<b>参考项评估</b>", heading_style))
        elements.append(Spacer(1, 10))

        for item in data["reference_items"]:
            elements.append(self._create_item_paragraph(item, normal_style, font_name))
            elements.append(Spacer(1, 5))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _create_item_paragraph(self, item: Dict[str, Any], style, font_name: str) -> Paragraph:
        """创建风险项段落"""
        status = item["status"]
        severity = item.get("severity", "")
        item_name = item["item_name"]
        data_source = item.get("data_source", "")

        # 根据状态确定颜色
        if status == "已触发":
            if severity == "严重":
                color = "#FF4B4B"
            else:
                color = "#FFD700"
        elif status == "异常":
            color = "#FF9800"
        else:
            color = "#808080"

        severity_text = f"[{severity}]" if severity else ""
        html = f"""
        <font name="{font_name}" color="{color}"><b>{item_name}</b></font> <font name="{font_name}">{severity_text}</font><br/>
        <font name="{font_name}">状态：<b>{status}</b> | 数据来源：{data_source}</font>
        """
        return Paragraph(html, style)