# -*- coding: utf-8 -*-
"""事件分类：将MT5日历导出的本地化事件名映射到规范类别（中英关键词表）。"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (规范类别, [关键词正则片段]) —— 按顺序匹配，先命中优先
CLASSIFIERS = [
    ("FOMC利率决议", ["fomc", "fed funds", "联邦基金", "利率决议", "rate decision", "interest rate", "货币政策"]),
    ("CPI通胀", ["cpi", "消费者物价", "通胀", "inflation", "核心cpi", "core cpi", "cpi指数"]),
    ("PCE通胀", ["pce", "个人消费支出"]),
    ("PPI生产者价格", ["ppi", "生产者物价", "生产者价格", "producer price"]),
    ("非农就业", ["nonfarm", "非农", "non-farm", "average hourly", "平均时薪", "平均每小时"]),
    ("失业率/初请", ["unemployment", "失业", "jobless", "初请", "claim", "chomage"]),
    ("GDP", ["gdp", "国内生产总值", "gross domestic"]),
    ("零售销售", ["retail", "零售销售", "零售"]),
    ("PMI景气", ["pmi", "采购经理", "ism manufacturing", "ism services", "制造业指数", "服务业指数"]),
    ("工业/耐用品", ["durable", "耐用品", "industrial production", "工业生产", "工厂订单", "factory order"]),
    ("EIA原油库存", ["eia", "crude oil invent", "原油库存", "库存变化", "api report", "api原油", "蒸馏", "distillate", "汽油库存"]),
    ("OPEC会议", ["opec", "欧佩克", "石油输出国"]),
    ("美债拍卖/收益率", ["treasury", "国债", "10-year", "10年期", "30-year", "30年期", "2-year", "2年期", "bond auction", "国债拍卖", "收益率", "yield"]),
    ("贸易帐", ["trade balance", "贸易帐", "贸易余额", "trade deficit", "贸易"]),
    ("房价/建筑", ["housing", "房屋", "building permit", "营建许可", "home sales", "成屋销售", "新屋"]),
    ("消费者信心", ["consumer confidence", "消费者信心", "密歇根", "michigan"]),
    ("耐用品订单", ["durable goods", "耐用品订单"]),
]

# 匹配时对事件名做小写化，中文关键词原样
def classify(event_name) -> str:
    if event_name is None or (isinstance(event_name, float) and event_name != event_name):
        return "其他"
    name = str(event_name)
    low = name.lower()
    for cat, kws in CLASSIFIERS:
        for kw in kws:
            if kw.lower() in low or kw in name:
                return cat
    return "其他"


if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        print(line.strip(), "->", classify(line.strip()))
