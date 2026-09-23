"""求職助手 Job Fit Assistant — 上傳履歷，比對 JobsDB 職位描述（JD）。"""
from __future__ import annotations

import time

import streamlit as st

import embeddings
import matcher
from resume_io import extract_text

st.set_page_config(page_title="求職助手 Job Fit Assistant", page_icon="💼", layout="wide")


# ---------- 函式定義（放在使用之前，避免 NameError） ----------

VERDICT_META = {
    "matched": "✅ 匹配 Matched",
    "partial": "⚠️ 部分 Partial",
    "gap": "❌ 缺口 Gap",
}


@st.cache_resource(show_spinner="正在載入模型 Loading model…（首次較慢）")
def _warmup() -> bool:
    embeddings.warmup()
    return True


@st.cache_data(show_spinner=False, ttl=3600)
def _run_analysis(resume_text: str, jd_text: str) -> dict:
    return matcher.analyze(resume_text, jd_text)


def _render_result(result: dict) -> None:
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("符合度 Fit Score", f"{result['fit_score']}%")
    c2.metric("匹配 Matched", result["matched"])
    c3.metric("部分 Partial", result["partial"])
    c4.metric("缺口 Gap", result["gap"])
    st.progress(result["fit_score"] / 100)

    st.subheader("📝 總結 Summary")
    st.write(result.get("summary", ""))

    with st.expander("📎 逐條細節與證據（點開查看）"):
        for r in result["requirements"]:
            label = VERDICT_META.get(r["verdict"], "?")
            st.markdown(f"**{label}** ｜ {r['requirement']}")
            st.markdown(f"- {r['reason']}")
            for e in r["evidence"]:
                st.markdown(f"  · 證據：{e}")


# ---------- 啟動時預先載入模型 ----------

_warmup()


# ---------- UI ----------

st.title("💼 求職助手 Job Fit Assistant")
st.caption("上傳履歷，貼上求職網站（JobsDB）的職位描述，即時比對你的符合度與差距。")

left, right = st.columns(2, gap="large")

with left:
    st.subheader("📄 你的履歷 Your Resume")
    resume_file = st.file_uploader("上傳履歷（PDF / DOCX / TXT）", type=["pdf", "docx", "txt"])
    resume_text = st.text_area("或直接貼上履歷文字 Or paste resume text", height=280)
    resume_content = extract_text(resume_file) if resume_file is not None else ""

with right:
    st.subheader("📋 職位描述 Job Description (JobsDB)")
    jd_file = st.file_uploader("上傳 JD 檔案（PDF / DOCX / TXT）", type=["pdf", "docx", "txt"])
    jd_text = st.text_area("或直接貼上 JD 文字 Or paste JD text", height=280)
    jd_content = extract_text(jd_file) if jd_file is not None else ""

resume_final = (resume_content or resume_text).strip()
jd_final = (jd_content or jd_text).strip()

analyze = st.button(
    "🔍 開始分析 Analyze",
    type="primary",
    disabled=not (resume_final and jd_final),
)

if analyze:
    t0 = time.time()
    with st.spinner("分析中 Analyzing…"):
        result = _run_analysis(resume_final, jd_final)
    elapsed = time.time() - t0

    if "error" in result:
        st.error(result["error"])
    else:
        st.caption(f"⏱ 耗時 {elapsed:.1f}s（相同輸入會直接讀快取）")
        _render_result(result)
