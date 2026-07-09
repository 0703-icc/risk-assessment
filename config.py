"""风险项配置模块

定义所有可评估的风险项，包括独立项和参考项。
"""

RISK_ITEMS = {
    "I-001": {
        "name": "公开市场债务实质性违约",
        "type": "独立项",
        "severity": "严重",
        "keywords": ["违约", "未能兑付", "债券逾期", "债务逾期"],
        "data_sources": ["bond_market", "news_api"]
    },
    "I-002": {
        "name": "被监管/司法立案调查",
        "type": "独立项",
        "severity": "严重",
        "keywords": ["立案调查", "涉嫌违规", "监管处罚", "证监会调查", "涉嫌违法"],
        "data_sources": ["news_api", "court_info"]
    },
    "I-003": {
        "name": "核心资产被司法查封/冻结",
        "type": "独立项",
        "severity": "严重",
        "keywords": ["查封", "冻结", "扣押", "司法"],
        "data_sources": ["court_info"]
    },
    "I-004": {
        "name": "实际控制人/控股股东变更",
        "type": "独立项",
        "severity": "警示",
        "keywords": ["实际控制人变更", "控股股东变更", "股权变更", "实控人"],
        "data_sources": ["news_api"]
    },
    "I-005": {
        "name": "项目实质性烂尾/长期停工",
        "type": "独立项",
        "severity": "警示",
        "keywords": ["烂尾", "停工", "延期交付", "逾期交房"],
        "data_sources": ["news_api", "government"]
    },
    "R-001": {
        "name": "高管频繁变动",
        "type": "参考项",
        "severity": None,
        "keywords": ["高管离职", "董事长辞职", "总经理变动", "人事变动", "核心高管离职"],
        "data_sources": ["news_api"]
    },
    "R-002": {
        "name": "负面舆情集中爆发",
        "type": "参考项",
        "severity": None,
        "keywords": ["维权", "投诉", "业主抗议", "群体性事件", "负面舆情"],
        "data_sources": ["news_api"]
    },
    "R-003": {
        "name": "因违规被暂停网签或预售审批",
        "type": "参考项",
        "severity": None,
        "keywords": ["暂停网签", "暂停预售", "违规", "行政处罚"],
        "data_sources": ["news_api", "government"]
    }
}

# 独立项子集（用于快速遍历）
INDEPENDENT_ITEMS = {
    code: item for code, item in RISK_ITEMS.items()
    if item["type"] == "独立项"
}

# 参考项子集
REFERENCE_ITEMS = {
    code: item for code, item in RISK_ITEMS.items()
    if item["type"] == "参考项"
}