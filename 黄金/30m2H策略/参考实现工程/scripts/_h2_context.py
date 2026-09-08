# -*- coding: utf-8 -*-
"""Shared H2 loading helpers for strategy-time alignment."""
from __future__ import annotations

import pandas as pd


H2_SOURCE_TO_CLIENT_HOURS = 0  # 服务器=UTC，无时区偏移
H2_BUCKET_TO_DECISION_HOURS = 2
H2_TOTAL_DECISION_SHIFT_HOURS = H2_SOURCE_TO_CLIENT_HOURS + H2_BUCKET_TO_DECISION_HOURS


def load_h2_context(path: str = "base_data/H2_XAUUSDm_39col.csv", extra_shift_hours: int = 0) -> pd.DataFrame:
    """Load H2 data on the strategy decision timeline.

    Raw H2 CSV timestamps are bucket start times derived from source M30 server time.
    Strategy scripts compare them against M30 client-time bar anchors and must use the
    latest completed H2 state. That requires:
    1. server time -> client time: +2h
    2. H2 bucket start -> next M30 decision anchor after H2 completion: +2h
    """
    h2 = pd.read_csv(path, encoding="utf-8-sig")
    source_time = pd.to_datetime(h2["date"])
    client_bucket_time = source_time + pd.Timedelta(hours=H2_SOURCE_TO_CLIENT_HOURS)
    decision_time = client_bucket_time + pd.Timedelta(hours=H2_BUCKET_TO_DECISION_HOURS + extra_shift_hours)

    h2["source_time"] = source_time
    h2["client_bucket_time"] = client_bucket_time
    h2["decision_time"] = decision_time
    h2["date"] = decision_time
    return h2
