"""Streamlit 主应用

风险项评估报告生成的 Web 界面。
"""

import streamlit as st
from datetime import datetime
from typing import List

from config import RISK_ITEMS, INDEPENDENT_ITEMS, REFERENCE_ITEMS
from database import init_db, save_report, save_risk_item, get_latest_report
from data_collector import DataCollector
from evaluators import IndependentEvaluator, ReferenceEvaluator
from report_generator import ReportGenerator
from stock_lookup import resolve_company_name

# 页面配置
st.set_page_config(
    page_title="开发商风险项评估",
    page_icon="🏗️",
    layout="wide"
)

# 初始化数据库
init_db()

# 初始化组件
data_collector = DataCollector()
independent_evaluator = IndependentEvaluator()
reference_evaluator = ReferenceEvaluator()
report_generator = ReportGenerator()

# 公司信息映射（股票代码 → 全称 → 简称）
COMPANY_INFO = {
    "000002": {"full_name": "万科企业股份有限公司", "short_name": "万科"},
    "600606": {"full_name": "绿地控股集团股份有限公司", "short_name": "绿地控股"},
    "600048": {"full_name": "保利发展控股集团股份有限公司", "short_name": "保利发展"},
    "1109": {"full_name": "华润置地有限公司", "short_name": "华润置地"},
    "001979": {"full_name": "招商局蛇口工业区控股股份有限公司", "short_name": "招商蛇口"},
    "00960": {"full_name": "龙湖集团控股有限公司", "short_name": "龙湖集团"},
    "2007": {"full_name": "碧桂园控股有限公司", "short_name": "碧桂园"},
    "1918": {"full_name": "融创中国控股有限公司", "short_name": "融创中国"},
    "600036": {"full_name": "招商银行股份有限公司", "short_name": "招商银行"},
    "601318": {"full_name": "中国平安保险（集团）股份有限公司", "short_name": "中国平安"},
}

# 动态识别结果缓存（公司名 → 股票代码）
# 用于保存通过股票代码接口自动识别的公司
_DYNAMIC_CODE_CACHE = {}

# 热门开发商快捷选择（股票代码）
HOT_COMPANIES = list(COMPANY_INFO.keys())

# 初始化搜索历史
if "search_history" not in st.session_state:
    st.session_state.search_history = []


def add_search_history(company_name: str):
    """添加搜索历史"""
    if company_name.strip():
        if company_name in st.session_state.search_history:
            st.session_state.search_history.remove(company_name)
        st.session_state.search_history.insert(0, company_name)
        if len(st.session_state.search_history) > 10:
            st.session_state.search_history = st.session_state.search_history[:10]


def parse_company_input(input_text: str) -> str:
    """解析用户输入，返回公司全称

    支持输入：股票代码、简称、全称
    """
    global _DYNAMIC_CODE_CACHE
    input_text = input_text.strip()

    # 1. 检查是否是预置股票代码
    if input_text in COMPANY_INFO:
        full_name = COMPANY_INFO[input_text]["full_name"]
        _DYNAMIC_CODE_CACHE[full_name] = input_text
        return full_name

    # 2. 尝试通过股票代码接口自动识别（支持任意A股/港股/美股）
    resolved = resolve_company_name(input_text)
    if resolved:
        company_name = resolved["name"]
        _DYNAMIC_CODE_CACHE[company_name] = resolved["code"]
        return company_name

    # 3. 检查是否匹配预置简称/全称
    for code, info in COMPANY_INFO.items():
        if input_text == info["short_name"] or input_text in info["short_name"]:
            _DYNAMIC_CODE_CACHE[info["full_name"]] = code
            return info["full_name"]
        if input_text == info["full_name"] or input_text in info["full_name"]:
            _DYNAMIC_CODE_CACHE[input_text] = code
            return input_text

    # 4. 返回原始输入（可能是未知公司）
    return input_text


def get_company_code(company_name: str) -> str:
    """根据公司名称查找股票代码

    Args:
        company_name: 公司全称或简称

    Returns:
        股票代码，如果找不到返回空字符串
    """
    # 1. 先查动态缓存
    if company_name in _DYNAMIC_CODE_CACHE:
        return _DYNAMIC_CODE_CACHE[company_name]

    # 2. 再查预置映射
    for code, info in COMPANY_INFO.items():
        if company_name == info["full_name"] or company_name in info["full_name"]:
            return code
        if company_name == info["short_name"] or company_name in info["short_name"]:
            return code
    return ""


def get_company_display_name(company_name: str) -> str:
    """获取公司显示名称（含股票代码）

    返回格式：名字（代码），例如：招商蛇口（001979）
    如果找不到代码，只返回公司名称
    """
    code = get_company_code(company_name)
    if code:
        # 预置映射中找简称
        for _, info in COMPANY_INFO.items():
            if company_name == info["full_name"]:
                return f"{info['short_name']}（{code}）"
        # 动态识别的公司直接用名字
        return f"{company_name}（{code}）"
    return company_name


def get_matching_history(query: str) -> List[str]:
    """获取匹配的历史记录"""
    if not query.strip():
        return []
    return [name for name in st.session_state.search_history if query in name]


def run_evaluation(company_name: str):
    """执行评估流程"""
    with st.spinner("正在采集数据并分析..."):
        # 1. 采集数据
        collected_data = data_collector.collect(company_name)
        all_data = []
        for source_data in collected_data.values():
            all_data.extend(source_data)

        # 2. 评估独立项（合并所有数据源）
        independent_results = []
        for code, config in INDEPENDENT_ITEMS.items():
            source_data = []
            for src_key in config["data_sources"]:
                source_data.extend(collected_data.get(src_key, []))
            result = independent_evaluator.evaluate(code, source_data)
            independent_results.append({
                "code": code,
                **result
            })

        # 3. 评估参考项（合并所有数据源）
        reference_results = []
        for code, config in REFERENCE_ITEMS.items():
            source_data = []
            for src_key in config["data_sources"]:
                source_data.extend(collected_data.get(src_key, []))
            result = reference_evaluator.evaluate(code, source_data)
            reference_results.append({
                "code": code,
                **result
            })

        # 4. 确定整体状态
        has_independent_risk = any(
            r["status"] == "已触发" for r in independent_results
        )
        has_reference_risk = any(
            r["status"] in ["轻度关注", "中度异常", "严重异常"]
            for r in reference_results
        )
        overall_status = "有风险" if (has_independent_risk or has_reference_risk) else "无风险"

        # 5. 保存报告
        data_sources = [k for k, v in collected_data.items() if v]
        report_id = save_report(company_name, data_sources, overall_status)

        # 6. 保存风险项
        for result in independent_results:
            evidence = result.get("evidence", [])
            first_evidence = evidence[0] if evidence else {}
            save_risk_item(
                report_id=report_id,
                item_code=result["code"],
                item_name=result["item_name"],
                item_type="独立项",
                status=result["status"],
                severity=result.get("severity"),
                data_source=first_evidence.get("source", ""),
                evidence_url=first_evidence.get("url", ""),
                description=first_evidence.get("title", ""),
                match_count=result.get("match_count", 0),
                total_data=result.get("total_data", 0),
            )

        for result in reference_results:
            evidence = result.get("evidence", [])
            first_evidence = evidence[0] if evidence else {}
            save_risk_item(
                report_id=report_id,
                item_code=result["code"],
                item_name=result["item_name"],
                item_type="参考项",
                status=result["status"],
                data_source=first_evidence.get("source", ""),
                evidence_url=first_evidence.get("url", ""),
                description=first_evidence.get("title", ""),
                match_count=result.get("match_count", 0),
                total_data=result.get("total_data", 0),
            )

        return report_id


def display_report(company_name: str):
    """展示评估报告"""
    data = report_generator.get_report_data(company_name)

    if not data:
        st.error("未找到评估报告")
        return

    report = data["report"]

    # 获取显示名称（含股票代码）
    display_name = get_company_display_name(company_name)

    # 报告头部
    st.header(f"📊 {display_name} 风险评估报告")
    st.caption(f"评估时间：{report['evaluation_time']} | 整体状态：{report['overall_status']}")

    # 独立项
    st.subheader("🔴 独立项评估")
    st.caption("独立项是二元事件，发生即构成风险信号")

    for item in data["independent_items"]:
        status = item["status"]
        severity = item.get("severity", "")
        item_name = item["item_name"]

        # 颜色标识
        if status == "已触发":
            if severity == "严重":
                color = "🔴"
                bg_color = "#FFEBEE"
            else:
                color = "🟡"
                bg_color = "#FFF8E1"
        elif status == "信息冲突":
            color = "🟠"
            bg_color = "#FFF3E0"
        else:
            color = "⚪"
            bg_color = "#F5F5F5"

        with st.container():
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <b>{color} {item_name}</b> <span style="color: {'#FF4B4B' if severity == '严重' else '#FFD700'}">[{severity}]</span><br/>
                <b>状态：{status}</b><br/>
                <small>数据来源：{item.get('data_source', 'N/A')} | 采集时间：{item.get('created_at', 'N/A')}</small>
            </div>
            """, unsafe_allow_html=True)

            # 详情展开
            if status in ["已触发", "信息冲突"]:
                with st.expander("查看详情"):
                    if item.get("evidence_url"):
                        st.markdown(f"**证据链接：** [{item['evidence_url']}]({item['evidence_url']})")
                    if item.get("description"):
                        st.markdown(f"**描述：** {item['description']}")

    # 参考项
    st.subheader("🔵 参考项评估")
    st.caption("参考项通过量化指标判断异常程度（匹配数/总数据量）")

    for item in data["reference_items"]:
        status = item["status"]
        item_name = item["item_name"]
        match_count = item.get("match_count", 0)
        total_data = item.get("total_data", 0)

        if status == "严重异常":
            color = "🔴"
            bg_color = "#FFEBEE"
            bar_color = "#FF4B4B"
        elif status == "中度异常":
            color = "🟠"
            bg_color = "#FFF3E0"
            bar_color = "#FF9800"
        elif status == "轻度关注":
            color = "🟡"
            bg_color = "#FFF8E1"
            bar_color = "#FFD700"
        elif status == "正常":
            color = "🟢"
            bg_color = "#E8F5E9"
            bar_color = "#4CAF50"
        else:
            color = "⚪"
            bg_color = "#F5F5F5"
            bar_color = "#9E9E9E"

        # 计算占比（用于进度条展示）
        ratio = match_count / total_data if total_data > 0 else 0
        ratio_pct = min(ratio * 100, 100)

        with st.container():
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <b>{color} {item_name}</b><br/>
                <b>状态：{status}</b> <span style="color: {bar_color};">（匹配 {match_count} 条 / 总数据 {total_data} 条）</span><br/>
                <div style="width: 100%; background-color: #E0E0E0; border-radius: 4px; margin-top: 8px;">
                    <div style="width: {ratio_pct}%; background-color: {bar_color}; height: 8px; border-radius: 4px;"></div>
                </div>
                <small>数据来源：{item.get('data_source', 'N/A')} | 采集时间：{item.get('created_at', 'N/A')}</small>
            </div>
            """, unsafe_allow_html=True)

    # PDF导出
    st.divider()
    if st.button("📄 导出PDF报告"):
        try:
            pdf_bytes = report_generator.generate_pdf(company_name)
            st.download_button(
                label="下载PDF",
                data=pdf_bytes,
                file_name=f"{company_name}_风险评估报告.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF导出失败：{str(e)}")


# 主界面
st.title("🏗️ 开发商风险项评估系统")

# 检查是否有历史报告需要展示
if "show_report" in st.session_state and st.session_state.show_report:
    company_name = st.session_state.company_name

    # 返回按钮
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← 返回"):
            st.session_state.show_report = False
            st.rerun()
    with col2:
        if st.button("🔄 重新评估"):
            run_evaluation(company_name)
            st.rerun()

    display_report(company_name)

else:
    # 处理快捷选择（在 text_input 渲染前设置初始值）
    if "selected_company" in st.session_state and st.session_state.selected_company:
        st.session_state.company_search_input = st.session_state.selected_company
        st.session_state.selected_company = ""

    st.markdown("### 🔍 搜索开发商")
    company_name = st.text_input(
        "开发商名称",
        placeholder="输入公司名称、简称或股票代码",
        label_visibility="collapsed",
        key="company_search_input"
    )

    # 搜索历史建议
    matching_history = get_matching_history(company_name)
    if matching_history:
        st.markdown("#### 📝 搜索历史")
        for idx, name in enumerate(matching_history[:5], 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"🔙 {name}", key=f"history_{idx}", use_container_width=True):
                    st.session_state.selected_company = name
                    st.rerun()
            with col2:
                latest_report = get_latest_report(name)
                if latest_report:
                    st.caption(f"最近评估: {latest_report['evaluation_time'][:10]}")

    # 热门开发商快捷选择
    st.markdown("#### ⭐ 热门开发商（股票代码）")
    hot_cols = st.columns(4)
    for idx, code in enumerate(HOT_COMPANIES):
        with hot_cols[idx % 4]:
            short_name = COMPANY_INFO[code]["short_name"]
            if st.button(f"{code} {short_name}", key=f"hot_{idx}", use_container_width=True):
                st.session_state.selected_company = code
                st.rerun()

    # 检查历史记录
    if company_name:
        # 解析为公司全称
        full_name = parse_company_input(company_name)
        
        # 显示解析后的全称
        if full_name != company_name:
            st.info(f"🔍 已识别：{company_name} → {full_name}")
        
        latest_report = get_latest_report(full_name)
        if latest_report:
            st.info(f"📋 发现历史评估记录（{latest_report['evaluation_time']}）")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("查看历史报告", type="secondary"):
                    st.session_state.show_report = True
                    st.session_state.company_name = full_name
                    add_search_history(full_name)
                    st.rerun()
            with col2:
                if st.button("重新评估", type="primary"):
                    run_evaluation(full_name)
                    st.session_state.show_report = True
                    st.session_state.company_name = full_name
                    add_search_history(full_name)
                    st.rerun()
        else:
            if st.button("开始评估", type="primary"):
                if not company_name.strip():
                    st.error("请输入开发商名称")
                else:
                    run_evaluation(full_name)
                    st.session_state.show_report = True
                    st.session_state.company_name = full_name
                    add_search_history(full_name)
                    st.rerun()
    else:
        st.button("开始评估", type="primary", disabled=True)

    # 说明
    st.divider()
    st.markdown("""
    ### 📋 评估说明

    本系统基于公开数据源，对开发商进行风险项评估，包括：

    **独立项（二元事件，发生即构成风险）**
    - 🔴 公开市场债务实质性违约（严重）
    - 🔴 被监管/司法立案调查（严重）
    - 🔴 核心资产被司法查封/冻结（严重）
    - 🟡 实际控制人/控股股东变更（警示）
    - 🟡 项目实质性烂尾/长期停工（警示）

    **参考项（量化分级判断异常）**
    - 高管频繁变动（匹配数分级：0=正常，1=轻度关注，2-3=中度异常，4+=严重异常）
    - 负面舆情集中爆发（匹配数分级：同上）
    - 因违规被暂停网签或预售审批（匹配数分级：同上）

    **数据源**：巨潮资讯网（上市公司公告）、百度新闻（真实新闻搜索）
    """)
