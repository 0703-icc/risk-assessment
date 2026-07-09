"""报告生成器

生成在线报告和PDF导出。
"""

import io
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
        styles = getSampleStyleSheet()

        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1  # 居中
        )

        # 报告标题
        elements.append(Paragraph(f"风险评估报告", title_style))
        elements.append(Spacer(1, 20))

        # 基本信息
        report = data["report"]
        elements.append(Paragraph(f"<b>开发商名称：</b>{report['company_name']}", styles['Normal']))
        elements.append(Paragraph(f"<b>评估时间：</b>{report['evaluation_time']}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # 独立项
        elements.append(Paragraph("<b>独立项评估</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))

        for item in data["independent_items"]:
            elements.append(self._create_item_paragraph(item, styles))
            elements.append(Spacer(1, 5))

        elements.append(Spacer(1, 20))

        # 参考项
        elements.append(Paragraph("<b>参考项评估</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))

        for item in data["reference_items"]:
            elements.append(self._create_item_paragraph(item, styles))
            elements.append(Spacer(1, 5))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _create_item_paragraph(self, item: Dict[str, Any], styles) -> Paragraph:
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
        <font color="{color}"><b>{item_name}</b></font> {severity_text}<br/>
        状态：<b>{status}</b> | 数据来源：{data_source}
        """
        return Paragraph(html, styles['Normal'])