"""共用的內建 AI 營運助理。

這個元件刻意不呼叫外部 AI 服務，直接以各系統現有的 DataFrame 產生可追溯的摘要，
因此不需要 API Token，也不會把內部請款、採購或報價資料傳出系統。
"""

from __future__ import annotations

import datetime as _datetime
from typing import Callable, Optional

import pandas as pd
import streamlit as st


def _column(df: pd.DataFrame, names: tuple[str, ...]) -> Optional[str]:
    for name in names:
        if name in df.columns:
            return name
    return None


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _amount(value: object) -> float:
    try:
        return float(str(value).replace(",", "").replace("$", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _visible_data(df: pd.DataFrame, current_user: str, is_admin: bool) -> pd.DataFrame:
    if df.empty or is_admin:
        return df.copy()
    user_columns = [
        column
        for column in ("申請人", "代申請人", "專案負責人", "負責人", "建立人")
        if column in df.columns
    ]
    if not user_columns:
        return df.copy()
    mask = pd.Series(False, index=df.index)
    for column in user_columns:
        mask = mask | df[column].astype(str).str.contains(current_user, regex=False, na=False)
    return df.loc[mask].copy()


def _money_total(df: pd.DataFrame) -> float:
    amount_column = _column(df, ("總金額", "金額", "預算", "採購金額", "報價金額"))
    if not amount_column:
        return 0.0
    return float(df[amount_column].map(_amount).sum())


def _status_counts(df: pd.DataFrame) -> str:
    status_column = _column(df, ("狀態", "進度", "工作狀態"))
    if not status_column or df.empty:
        return "目前沒有可統計的狀態資料。"
    counts = df[status_column].astype(str).replace("", "未設定").value_counts().head(8)
    return "、".join(f"{_text(label)} {count} 筆" for label, count in counts.items())


def _rows_preview(df: pd.DataFrame, limit: int = 5) -> str:
    if df.empty:
        return "目前沒有符合條件的資料。"
    id_column = _column(df, ("單號", "申請單號", "編號"))
    project_column = _column(df, ("專案名稱", "專案", "名稱"))
    status_column = _column(df, ("狀態", "進度", "工作狀態"))
    amount_column = _column(df, ("總金額", "金額", "預算", "採購金額", "報價金額"))
    lines = []
    for _, row in df.head(limit).iterrows():
        parts = []
        if id_column:
            parts.append(_text(row.get(id_column)))
        if project_column:
            parts.append(_text(row.get(project_column)))
        if amount_column and _amount(row.get(amount_column)):
            parts.append(f"${_amount(row.get(amount_column)):,.0f}")
        if status_column and _text(row.get(status_column)):
            parts.append(_text(row.get(status_column)))
        lines.append("／".join(parts) or "未命名資料")
    return "、".join(lines)


def _assistant_answer(query: str, df: pd.DataFrame, system_name: str, current_user: str, is_admin: bool) -> str:
    data = _visible_data(df, current_user, is_admin)
    status_column = _column(data, ("狀態", "進度", "工作狀態"))
    query = query.strip()
    normalized = query.replace(" ", "").lower()
    total = _money_total(data)
    pending = pd.DataFrame()
    if status_column:
        pending = data[data[status_column].astype(str).str.contains("待簽核|待初審|待複審|待辦|進行中", regex=True, na=False)]
    delayed = pd.DataFrame()
    if status_column:
        delayed = data[data[status_column].astype(str).str.contains("延遲|逾期", regex=True, na=False)]

    if any(word in normalized for word in ("今日任務", "今天任務", "today")):
        date_column = _column(data, ("日期", "建立日期", "提交時間", "截止日期", "預計完成日"))
        if date_column:
            today_token = _datetime.date.today().strftime("%Y%m%d")
            today = data[data[date_column].astype(str).str.replace("-", "", regex=False).str.contains(today_token, regex=False, na=False)]
            return f"📌 {system_name} 今日資料：{len(today)} 筆。\n{_rows_preview(today)}"
        return f"📌 {system_name} 目前共 {len(data)} 筆資料；待處理 {len(pending)} 筆。\n{_rows_preview(pending)}"

    if any(word in normalized for word in ("延遲", "逾期", "風險")):
        return f"⏰ 目前辨識到 {len(delayed)} 筆延遲／逾期資料。\n{_rows_preview(delayed)}" if not delayed.empty else "✅ 目前沒有明確標記為延遲或逾期的資料。"

    if any(word in normalized for word in ("簽核", "待辦", "交接", "handoff")):
        return f"🔄 待處理／待簽核共 {len(pending)} 筆。\n建議交接重點：{_rows_preview(pending)}" if not pending.empty else "✅ 目前沒有待簽核或待辦資料。"

    if any(word in normalized for word in ("財務", "金額", "收支", "finance")):
        return f"💰 可見資料共 {len(data)} 筆，金額合計 ${total:,.0f}。\n狀態分布：{_status_counts(data)}"

    if any(word in normalized for word in ("負載", "工作量", "人力", "workload")):
        person_column = _column(data, ("專案負責人", "負責人", "申請人", "建立人"))
        if person_column and not data.empty:
            workload = data[person_column].astype(str).replace("", "未指定").value_counts().head(8)
            return "📊 工作量分布：" + "、".join(f"{_text(name)} {count} 筆" for name, count in workload.items())
        return "目前資料沒有可辨識的負責人欄位。"

    if any(word in normalized for word in ("進度", "專案", "project")):
        return f"📈 {system_name} 共 {len(data)} 筆資料，待處理 {len(pending)} 筆。\n狀態分布：{_status_counts(data)}"

    if any(word in normalized for word in ("日報", "報告", "摘要")):
        return (
            f"📝 日報草稿（{_datetime.date.today().isoformat()}）\n"
            f"系統：{system_name}\n"
            f"資料筆數：{len(data)}；待處理：{len(pending)}；延遲／逾期：{len(delayed)}；金額合計：${total:,.0f}\n"
            f"狀態分布：{_status_counts(data)}\n"
            "建議明日追蹤：優先處理待簽核與延遲資料。"
        )

    if query:
        return f"🔎 我已在「{system_name}」查詢：{query}\n目前可見資料 {len(data)} 筆，待處理 {len(pending)} 筆，金額合計 ${total:,.0f}。\n可再試：今日任務、延遲項目、專案進度、工作負載、財務摘要、交接提醒、建立日報。"
    return f"👋 目前位於「{system_name}」。可見資料 {len(data)} 筆；可直接點選下方常用查詢。"


def render_ai_operations_assistant(
    system_name: str,
    data_loader: Callable[[], pd.DataFrame],
    current_user: str,
    is_admin: bool = False,
    key_prefix: str = "system",
) -> None:
    """Show the temporarily disabled assistant entry without exposing its controls."""
    st.sidebar.button(
        "✦ AI 營運助理（暫停）",
        key=f"ai_disabled_{key_prefix}",
        disabled=True,
        use_container_width=True,
    )
    return

    # 保留以下實作，日後重新啟用時只需移除上面的停用區塊。
    query_key = f"ai_ops_query_{key_prefix}"
    answer_key = f"ai_ops_answer_{key_prefix}"
    if answer_key not in st.session_state:
        st.session_state[answer_key] = ""

    with st.sidebar.expander("✦ AI 營運助理", expanded=False):
        st.markdown(f"### ✦ AI 營運助理\n目前系統：**{system_name}**")
        st.caption("內建資料助理｜只讀取目前系統資料，不需要外部 API Token")
        st.markdown("**常用查詢**")
        shortcuts = [
            ("今日任務", "今日任務"),
            ("延遲項目", "延遲項目"),
            ("專案進度", "專案進度"),
            ("工作負載", "工作負載"),
            ("財務摘要", "財務摘要"),
            ("交接提醒", "交接提醒"),
            ("建立日報草稿", "建立日報"),
        ]
        shortcut_query = None
        for label, shortcut in shortcuts:
            if st.button(label, key=f"ai_shortcut_{key_prefix}_{label}", use_container_width=True):
                shortcut_query = shortcut

        input_query = st.text_input(
            "可查詢，也可輸入現場資訊建立日報",
            key=query_key,
            placeholder="例如：請整理本週待簽核與延遲項目",
        )
        if st.button("➤ 查詢", key=f"ai_submit_{key_prefix}", use_container_width=True):
            shortcut_query = input_query or ""

        if shortcut_query is not None:
            try:
                data = data_loader()
                if not isinstance(data, pd.DataFrame):
                    data = pd.DataFrame(data)
                st.session_state[answer_key] = _assistant_answer(shortcut_query, data, system_name, current_user, is_admin)
            except Exception:
                st.session_state[answer_key] = "目前無法讀取系統資料，請稍後再試。"

        if st.session_state[answer_key]:
            st.divider()
            st.markdown(st.session_state[answer_key])
