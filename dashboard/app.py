"""
FabIQ Streamlit Dashboard — premium reviewer UI.

Run with:
    PYTHONPATH=src streamlit run dashboard/app.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FabIQ: Engineering Knowledge Intelligence",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Premium theme + animation CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
:root {
  --ink:#101828;
  --muted:#667085;
  --subtle:#98a2b3;
  --line:rgba(16,24,40,.10);
  --blue:#3758f9;
  --cyan:#00b8d9;
  --purple:#7c3aed;
  --green:#12b76a;
  --amber:#f79009;
  --red:#f04438;
  --card:rgba(255,255,255,.86);
  --shadow:0 24px 80px rgba(15,23,42,.12);
}

[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 10% 8%, rgba(55,88,249,.16), transparent 30%),
    radial-gradient(circle at 78% 0%, rgba(124,58,237,.13), transparent 31%),
    radial-gradient(circle at 90% 72%, rgba(0,184,217,.10), transparent 28%),
    linear-gradient(180deg,#f7f9ff 0%,#ffffff 44%,#f8fbff 100%);
}
[data-testid="stSidebar"] {
  background:linear-gradient(180deg,rgba(255,255,255,.97),rgba(245,248,255,.94));
  border-right:1px solid var(--line);
}
.block-container { padding-top:1.25rem; max-width:1440px; }

/* Streamlit widget polish */
[data-testid="stButton"] button {
  border-radius:16px!important;
  min-height:3rem;
  font-weight:850!important;
  letter-spacing:-.01em;
  box-shadow:0 12px 26px rgba(55,88,249,.18);
  transition:transform .16s ease, box-shadow .16s ease, filter .16s ease;
}
[data-testid="stButton"] button:hover { transform:translateY(-2px); box-shadow:0 18px 34px rgba(55,88,249,.24); filter:saturate(1.12); }
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input, [data-testid="stSelectbox"] div { border-radius:14px!important; }

/* Hero */
.fq-hero {
  position:relative; overflow:hidden; color:white;
  padding:34px 38px; border-radius:32px; margin-bottom:22px;
  background:
    linear-gradient(120deg, rgba(12,19,42,.98), rgba(38,55,147,.96) 52%, rgba(124,58,237,.90));
  box-shadow: var(--shadow);
  border:1px solid rgba(255,255,255,.15);
}
.fq-hero:before,.fq-hero:after{content:"";position:absolute;border-radius:999px;filter:blur(2px);}
.fq-hero:before{width:330px;height:330px;right:-95px;top:-125px;background:radial-gradient(circle,rgba(0,184,217,.55),transparent 68%);animation:orb 9s ease-in-out infinite;}
.fq-hero:after{width:310px;height:310px;left:-80px;bottom:-150px;background:radial-gradient(circle,rgba(18,183,106,.35),transparent 70%);animation:orb 10s ease-in-out infinite reverse;}
.fq-hero h1{position:relative;margin:0 0 10px;font-size:3.05rem;line-height:1.02;letter-spacing:-.065em;}
.fq-hero p{position:relative;margin:0;max-width:820px;color:rgba(255,255,255,.82);font-size:1.03rem;}
.fq-pills{position:relative;display:flex;gap:10px;flex-wrap:wrap;margin-top:20px;}
.fq-pill{display:inline-flex;gap:8px;align-items:center;border-radius:999px;padding:9px 13px;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(12px);font-size:.86rem;color:rgba(255,255,255,.93);}

/* Cards */
.fq-card,.fq-panel,.fq-answer,.fq-source,.fq-metric {
  background:var(--card); border:1px solid var(--line); box-shadow:0 18px 46px rgba(31,41,85,.07); backdrop-filter:blur(16px);
}
.fq-card{border-radius:24px;padding:22px;animation:rise .48s ease both;}
.fq-panel{border-radius:28px;padding:26px;margin-bottom:18px;animation:rise .52s ease both;}
.fq-answer{border-radius:26px;padding:24px 26px;margin:12px 0;background:linear-gradient(180deg,rgba(255,255,255,.96),rgba(249,251,255,.96));}
.fq-answer h3,.fq-panel h3,.fq-card h3{margin-top:0;letter-spacing:-.025em;}
.fq-muted{color:var(--muted);font-size:.93rem;line-height:1.5;}
.fq-small{color:var(--subtle);font-size:.83rem;}
.fq-section-title{font-size:1.25rem;font-weight:900;letter-spacing:-.035em;margin:2px 0 6px;color:#182230;}

/* Upload studio */
.fq-upload-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:10px;}
.fq-mode-badge{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:8px 12px;background:rgba(55,88,249,.10);color:#263fb0;border:1px solid rgba(55,88,249,.16);font-weight:800;font-size:.82rem;}
.fq-kpi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0 4px;}
.fq-kpi{border-radius:18px;padding:14px;background:rgba(255,255,255,.70);border:1px solid var(--line);}
.fq-kpi .label{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;font-weight:850;}
.fq-kpi .value{font-size:1.45rem;font-weight:950;color:#182230;letter-spacing:-.04em;}

/* Animated timeline */
.fq-timeline{position:relative;margin:16px 0 6px;padding-left:8px;}
.fq-step{position:relative;display:flex;gap:14px;align-items:flex-start;padding:10px 0 14px;animation:rise .45s ease both;}
.fq-step:not(:last-child):after{content:"";position:absolute;left:17px;top:40px;width:2px;height:calc(100% - 24px);background:linear-gradient(180deg,rgba(55,88,249,.22),rgba(55,88,249,.05));}
.fq-dot{position:relative;z-index:1;width:36px;height:36px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-weight:900;color:white;background:linear-gradient(135deg,var(--blue),var(--purple));box-shadow:0 10px 22px rgba(55,88,249,.20);}
.fq-dot.pending{background:#eef2f6;color:#667085;box-shadow:none;}
.fq-dot.active{background:linear-gradient(135deg,var(--amber),var(--purple));animation:pulse 1.15s infinite;}
.fq-dot.done{background:linear-gradient(135deg,var(--green),var(--cyan));}
.fq-step-body{flex:1;}
.fq-step-title{font-weight:900;color:#182230;margin-bottom:2px;letter-spacing:-.015em;}
.fq-step-desc{color:var(--muted);font-size:.88rem;line-height:1.42;}
.fq-step-status{font-size:.76rem;font-weight:900;text-transform:uppercase;letter-spacing:.08em;color:#667085;margin-top:5px;}
.fq-step-status.done{color:#027a48}.fq-step-status.active{color:#b54708}.fq-step-status.pending{color:#98a2b3}

/* Agent cards */
.fq-agent-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:14px;}
.fq-agent{position:relative;overflow:hidden;min-height:162px;border-radius:22px;padding:16px;background:rgba(255,255,255,.82);border:1px solid var(--line);box-shadow:0 12px 30px rgba(31,41,85,.06);transition:transform .18s ease,box-shadow .18s ease;animation:rise .56s ease both;}
.fq-agent:hover{transform:translateY(-5px);box-shadow:0 22px 46px rgba(31,41,85,.11)}
.fq-agent:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(55,88,249,.11),transparent);transform:translateX(-125%);animation:shimmer 5s infinite;}
.fq-agent-num{width:38px;height:38px;border-radius:14px;background:linear-gradient(135deg,var(--blue),var(--purple));display:flex;align-items:center;justify-content:center;color:#fff;font-weight:950;margin-bottom:11px;box-shadow:0 10px 20px rgba(55,88,249,.22)}
.fq-agent-title{font-weight:950;color:#182230;margin-bottom:5px;letter-spacing:-.02em;}
.fq-agent-desc{color:var(--muted);font-size:.84rem;line-height:1.38;}
.fq-agent-meta{position:absolute;bottom:14px;left:16px;right:16px;color:var(--subtle);font-size:.76rem;font-weight:800;}

/* Chat style */
.fq-chat-user{max-width:78%;margin:12px 0 12px auto;padding:15px 17px;border-radius:22px 22px 6px 22px;background:linear-gradient(135deg,var(--blue),var(--purple));color:white;box-shadow:0 16px 34px rgba(55,88,249,.22);font-weight:650;}
.fq-chat-assistant{max-width:92%;margin:12px auto 16px 0;padding:18px 20px;border-radius:22px 22px 22px 6px;background:rgba(255,255,255,.94);border:1px solid rgba(55,88,249,.14);box-shadow:0 16px 34px rgba(31,41,85,.07);}
.fq-chat-label{font-size:.76rem;text-transform:uppercase;letter-spacing:.09em;font-weight:950;color:#667085;margin-bottom:8px;}

/* Source + metrics */
.fq-source{border-radius:18px;padding:13px 15px;margin:8px 0;transition:transform .16s ease,border-color .16s ease;}
.fq-source:hover{transform:translateY(-2px);border-color:rgba(55,88,249,.26)}
.fq-source-title{font-weight:950;color:#182230}.fq-source-meta{color:var(--muted);font-size:.83rem;margin-top:3px}.fq-source-snippet{color:#475467;font-size:.86rem;margin-top:8px;line-height:1.44;}
.fq-latency-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid rgba(16,24,40,.08);font-size:.9rem;}
.fq-bar{height:8px;width:96px;background:#eef2ff;border-radius:999px;overflow:hidden}.fq-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--blue),var(--cyan));animation:grow .72s ease both;}
.fq-banner{border-radius:18px;padding:13px 15px;margin:12px 0;border:1px solid rgba(18,183,106,.20);background:linear-gradient(90deg,rgba(18,183,106,.10),rgba(0,184,217,.08));color:#05603a;}
.fq-warning{border-radius:18px;padding:13px 15px;margin:12px 0;border:1px solid rgba(247,144,9,.28);background:linear-gradient(90deg,rgba(247,144,9,.12),rgba(255,255,255,.70));color:#7a4b00;}
.fq-code{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;background:rgba(16,24,40,.06);padding:2px 6px;border-radius:7px;}


/* Premium live backend process board */
.fq-process-board{border-radius:28px;padding:22px;margin:16px 0;background:linear-gradient(180deg,rgba(255,255,255,.94),rgba(245,248,255,.92));border:1px solid rgba(55,88,249,.14);box-shadow:0 22px 56px rgba(31,41,85,.09);overflow:hidden;position:relative;}
.fq-process-board:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 12% 0%,rgba(55,88,249,.10),transparent 34%),radial-gradient(circle at 86% 20%,rgba(124,58,237,.09),transparent 36%);pointer-events:none;}
.fq-process-head{position:relative;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:18px;}
.fq-process-eyebrow{font-size:.76rem;text-transform:uppercase;letter-spacing:.12em;font-weight:950;color:#3758f9;margin-bottom:4px;}
.fq-process-title{font-size:1.35rem;font-weight:950;letter-spacing:-.04em;color:#182230;margin:0;}
.fq-live-badge{position:relative;display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:8px 12px;background:rgba(18,183,106,.12);color:#027a48;border:1px solid rgba(18,183,106,.20);font-weight:900;font-size:.80rem;white-space:nowrap;}
.fq-live-dot{width:8px;height:8px;border-radius:50%;background:#12b76a;box-shadow:0 0 0 0 rgba(18,183,106,.42);animation:livePulse 1.35s infinite;}
.fq-process-grid{position:relative;display:grid;grid-template-columns:repeat(5,1fr);gap:12px;}
.fq-process-card{position:relative;min-height:150px;border-radius:22px;padding:16px;background:rgba(255,255,255,.78);border:1px solid rgba(16,24,40,.10);box-shadow:0 12px 30px rgba(31,41,85,.06);overflow:hidden;}
.fq-process-card:after{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:#e4e7ec;}
.fq-process-card.done:after{background:linear-gradient(90deg,#12b76a,#00b8d9);}
.fq-process-card.active{border-color:rgba(55,88,249,.34);box-shadow:0 20px 48px rgba(55,88,249,.14);transform:translateY(-3px);}
.fq-process-card.active:before{content:"";position:absolute;inset:0;background:linear-gradient(100deg,transparent,rgba(55,88,249,.13),transparent);transform:translateX(-120%);animation:shimmer 1.5s infinite;}
.fq-process-card.active:after{background:linear-gradient(90deg,#3758f9,#7c3aed,#00b8d9);animation:loadingBar 1.3s ease-in-out infinite;}
.fq-process-icon{width:42px;height:42px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-weight:950;color:#667085;background:#eef2f6;margin-bottom:12px;}
.fq-process-card.done .fq-process-icon{color:white;background:linear-gradient(135deg,#12b76a,#00b8d9);}
.fq-process-card.active .fq-process-icon{color:white;background:linear-gradient(135deg,#3758f9,#7c3aed);animation:pulse 1.15s infinite;}
.fq-process-name{font-weight:950;color:#182230;letter-spacing:-.02em;margin-bottom:6px;}
.fq-process-copy{color:#667085;font-size:.84rem;line-height:1.42;}
.fq-process-status{margin-top:12px;font-size:.72rem;text-transform:uppercase;letter-spacing:.10em;font-weight:950;color:#98a2b3;}
.fq-process-card.done .fq-process-status{color:#027a48;}.fq-process-card.active .fq-process-status{color:#3758f9;}
.fq-step-summary{position:relative;margin-top:16px;border-radius:20px;padding:16px;background:rgba(55,88,249,.07);border:1px solid rgba(55,88,249,.12);color:#344054;line-height:1.5;}
.fq-step-summary strong{color:#182230;}
@keyframes livePulse{0%{box-shadow:0 0 0 0 rgba(18,183,106,.42)}70%{box-shadow:0 0 0 10px rgba(18,183,106,0)}100%{box-shadow:0 0 0 0 rgba(18,183,106,0)}}
@keyframes loadingBar{0%{transform:translateX(-70%)}50%{transform:translateX(0)}100%{transform:translateX(70%)}}
@media(max-width:1180px){.fq-process-grid{grid-template-columns:1fr}.fq-process-card{min-height:auto}}

@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@keyframes shimmer{0%{transform:translateX(-125%)}45%,100%{transform:translateX(125%)}}
@keyframes pulse{0%,100%{transform:scale(1);box-shadow:0 0 0 0 rgba(247,144,9,.32)}50%{transform:scale(1.04);box-shadow:0 0 0 12px rgba(247,144,9,0)}}
@keyframes grow{from{width:0}}
@keyframes orb{0%,100%{transform:translate3d(0,0,0)}50%{transform:translate3d(-25px,18px,0)}}
@media(max-width:1180px){.fq-agent-grid{grid-template-columns:1fr 1fr}.fq-kpi-grid{grid-template-columns:1fr}.fq-hero h1{font-size:2.25rem}}
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@st.cache_data(ttl=2, show_spinner=False)
def get_local_index_stats(index_path: str) -> tuple[int, int]:
    path = Path(index_path)
    if not path.exists():
        return 0, 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        docs = payload.get("documents", [])
        return len(docs), len({d.get("doc_id") for d in docs})
    except Exception:
        return 0, 0


def pretty_source(source: str) -> str:
    if not source:
        return "Unknown source"
    return Path(source).name or source


def short(text: str, n: int = 230) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def html_escape(text: Any) -> str:
    import html

    return html.escape(str(text))


INGEST_STEPS = [
    ("Upload received", "The file is accepted by the UI and passed into the ingestion worker."),
    ("Text extraction", "FabIQ extracts readable text and metadata from the uploaded document."),
    ("Chunking", "The document is split into overlapping source chunks for retrieval."),
    ("Embedding", "Each chunk is converted into a vector representation."),
    ("Index write", "Chunks, metadata, permissions, and vectors are stored in the active index."),
    ("Ready for retrieval", "The document is now searchable through the RAG pipeline."),
]

PIPELINE_STEPS = [
    ("Query understanding", "Classifies intent, extracts key entities, and prepares the retrieval query."),
    ("Privilege check", "Applies RBAC so the user only sees permitted source chunks."),
    ("Hybrid retrieval", "Finds the most relevant chunks from Azure Search or the local index."),
    ("Citation grounding", "Builds an answer from retrieved evidence and attaches citations."),
    ("Quality evaluation", "Scores answer accuracy, grounding, completeness, and confidence."),
]


def render_timeline(steps: list[tuple[str, str]], active: int = -1, done: int = -1) -> str:
    rows = ['<div class="fq-timeline">']
    for i, (title, desc) in enumerate(steps):
        if i <= done:
            cls, icon, status = "done", "✓", "complete"
        elif i == active:
            cls, icon, status = "active", str(i + 1), "running"
        else:
            cls, icon, status = "pending", str(i + 1), "waiting"
        rows.append(
            "".join(
                [
                    '<div class="fq-step">',
                    f'<div class="fq-dot {cls}">{html_escape(icon)}</div>',
                    '<div class="fq-step-body">',
                    f'<div class="fq-step-title">{html_escape(title)}</div>',
                    f'<div class="fq-step-desc">{html_escape(desc)}</div>',
                    f'<div class="fq-step-status {cls}">{status}</div>',
                    '</div>',
                    '</div>',
                ]
            )
        )
    rows.append('</div>')
    return ''.join(rows)



def render_process_board(
    steps: list[tuple[str, str]],
    active: int = -1,
    done: int = -1,
    summaries: list[dict[str, str]] | None = None,
    title: str = "Live backend process",
    subtitle: str = "What FabIQ is doing after the user submits a prompt.",
) -> str:
    """Render the five-step process as real HTML, not Markdown/code text."""
    summary_map = {item.get("step", ""): item.get("summary", "") for item in (summaries or [])}
    cards: list[str] = []
    for i, (name, desc) in enumerate(steps):
        if i <= done:
            cls, icon, status = "done", "✓", "Complete"
        elif i == active:
            cls, icon, status = "active", str(i + 1), "Running now"
        else:
            cls, icon, status = "pending", str(i + 1), "Waiting"
        copy = summary_map.get(name) or desc
        cards.append(
            "".join(
                [
                    f'<div class="fq-process-card {cls}">',
                    f'<div class="fq-process-icon">{html_escape(icon)}</div>',
                    f'<div class="fq-process-name">{html_escape(name)}</div>',
                    f'<div class="fq-process-copy">{html_escape(copy)}</div>',
                    f'<div class="fq-process-status">{html_escape(status)}</div>',
                    '</div>',
                ]
            )
        )
    badge_text = "Live" if active >= 0 else "Process map"
    live = f'<span class="fq-live-badge"><span class="fq-live-dot"></span>{badge_text}</span>'
    return "".join(
        [
            '<div class="fq-process-board">',
            '<div class="fq-process-head">',
            '<div>',
            '<div class="fq-process-eyebrow">Behind the scenes</div>',
            f'<div class="fq-process-title">{html_escape(title)}</div>',
            f'<div class="fq-muted">{html_escape(subtitle)}</div>',
            '</div>',
            live,
            '</div>',
            f'<div class="fq-process-grid">{"".join(cards)}</div>',
            '</div>',
        ]
    )


def render_process_summary(trace: list[dict[str, str]] | None) -> str:
    if not trace:
        return ""
    rows = []
    for item in trace:
        rows.append(
            f"""
            <div class="fq-step-summary">
              <strong>{html_escape(item.get('step', 'Step'))}</strong><br/>
              {html_escape(item.get('summary', ''))}
            </div>
            """
        )
    return "".join(rows)


def render_agent_cards(mode: str) -> None:
    st.markdown(
        f"""
        <div class="fq-agent-grid">
          <div class="fq-agent"><div class="fq-agent-num">1</div><div class="fq-agent-title">Query understanding</div><div class="fq-agent-desc">Transforms the user question into a retrieval-ready intent and entity set.</div><div class="fq-agent-meta">Mode: {html_escape(mode)}</div></div>
          <div class="fq-agent"><div class="fq-agent-num">2</div><div class="fq-agent-title">Privilege check</div><div class="fq-agent-desc">Filters access by role before retrieval, preventing restricted context leakage.</div><div class="fq-agent-meta">RBAC enforced server-side</div></div>
          <div class="fq-agent"><div class="fq-agent-num">3</div><div class="fq-agent-title">Retrieval</div><div class="fq-agent-desc">Searches Azure AI Search in production or local vector index in reviewer mode.</div><div class="fq-agent-meta">Top-k source selection</div></div>
          <div class="fq-agent"><div class="fq-agent-num">4</div><div class="fq-agent-title">Citation grounding</div><div class="fq-agent-desc">Creates a grounded answer and maps claims back to source chunks.</div><div class="fq-agent-meta">No citation, no claim</div></div>
          <div class="fq-agent"><div class="fq-agent-num">5</div><div class="fq-agent-title">Quality eval</div><div class="fq-agent-desc">Scores accuracy, grounding, completeness, and decides if review is needed.</div><div class="fq-agent-meta">HITL-ready output</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


async def ingest_uploaded_file(uploaded_file, access_level: str, chunk_strategy: str, chunk_size: int, chunk_overlap: int):
    from fabiq.api.models import IngestRequest
    from fabiq.api.routes.ingest import _run_ingestion
    from fabiq.config import get_settings
    from fabiq.retrieval.search import FabIQSearchClient

    cfg = get_settings()
    if cfg.app_mode == "local":
        from fabiq.retrieval.local_search import LocalSearchClient

        search_client = LocalSearchClient(cfg)
    else:
        search_client = FabIQSearchClient(cfg)

    suffix = Path(uploaded_file.name).suffix.lower() or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = Path(tmp.name)

    try:
        req = IngestRequest(
            access_level=access_level,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            extra_metadata={"filename": uploaded_file.name},
        )
        return await _run_ingestion(tmp_path, uploaded_file.name, req, search_client)
    finally:
        tmp_path.unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Session state + config
# ──────────────────────────────────────────────────────────────────────────────
for key, default in {
    "history": [],
    "last_result": None,
    "last_ingest": None,
    "ingest_trace": None,
    "pipeline_trace": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

try:
    from fabiq.config import get_settings

    cfg = get_settings()
except Exception as exc:
    cfg = None
    st.error(f"Configuration error: {exc}")

mode = getattr(cfg, "app_mode", "unknown")
index_path = getattr(cfg, "local_index_path", "data/local_index.json")
chunk_count, doc_count = get_local_index_stats(index_path)

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ FabIQ Control Center")
    st.caption("Engineering Knowledge Intelligence")
    st.markdown(
        f"""
        <div class="fq-banner">
          <strong>Runtime:</strong> {html_escape(mode).upper()}<br/>
          <strong>Indexed chunks:</strong> {chunk_count}<br/>
          <strong>Indexed docs:</strong> {doc_count}
        </div>
        """,
        unsafe_allow_html=True,
    )

    role = st.selectbox(
        "User role",
        ["field_engineer", "process_engineer", "admin"],
        index=1,
        help="Role-based access control changes which chunks can be retrieved.",
    )
    role_badge = {
        "field_engineer": "🟡 Public only",
        "process_engineer": "🟠 Public + Internal",
        "admin": "🔴 Public + Internal + Restricted",
    }
    st.caption(role_badge[role])

    top_k = st.slider("Source chunks to retrieve", 1, 10, 5)
    st.divider()

    if st.button("Clear current answer", use_container_width=True):
        st.session_state.last_result = None
        st.session_state.pipeline_trace = None
        st.rerun()

    try:
        from fabiq.pipeline.prompt_registry import get_active_version, get_changelog

        active_v = get_active_version()
        st.caption(f"Prompt version: **{active_v}**")
        with st.expander("Prompt changelog"):
            for entry in get_changelog():
                st.caption(f"**{entry['version']}** ({entry['date']})  \\n{entry['change']}")
    except Exception:
        st.caption("Prompt registry: unavailable")

# ──────────────────────────────────────────────────────────────────────────────
# Hero
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div class="fq-hero">
  <h1>FabIQ: Engineering Knowledge Intelligence</h1>
  <p>A premium reviewer dashboard for privilege-aware RAG. Upload documents, watch ingestion happen, query the knowledge base, and inspect each backend step like a transparent AI system.</p>
  <div class="fq-pills">
    <span class="fq-pill">⚡ 5-agent pipeline</span>
    <span class="fq-pill">🔐 RBAC retrieval</span>
    <span class="fq-pill">📚 Citation grounding</span>
    <span class="fq-pill">🧪 Runtime: {html_escape(mode)}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Main layout tabs
ask_tab, ingest_tab, explain_tab = st.tabs(["💬 Ask FabIQ", "📤 Upload & Index", "🧠 Backend Process"])

# ──────────────────────────────────────────────────────────────────────────────
# Upload and ingestion tab
# ──────────────────────────────────────────────────────────────────────────────
with ingest_tab:
    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        st.markdown(
            f"""
            <div class="fq-panel">
              <div class="fq-upload-head">
                <div>
                  <div class="fq-section-title">Document ingestion studio</div>
                  <div class="fq-muted">Upload a PDF, Markdown, or text file. FabIQ will parse, chunk, embed, permission-tag, and index it.</div>
                </div>
                <span class="fq-mode-badge">{html_escape(mode).upper()} MODE</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Choose a document", type=["pdf", "txt", "md", "mdx", "rst"])
        c1, c2 = st.columns(2)
        with c1:
            access_level = st.selectbox("Access level", ["public", "internal", "restricted"], index=0)
            chunk_size = st.slider("Chunk size", 128, 2048, 512, step=64)
        with c2:
            chunk_strategy = st.selectbox("Chunk strategy", ["recursive", "fixed", "semantic"], index=0)
            chunk_overlap = st.slider("Chunk overlap", 0, 256, 64, step=16)
        ingest_btn = st.button("✨ Index document with live backend trace", type="primary", use_container_width=True, disabled=uploaded is None)

        if ingest_btn and uploaded is not None:
            trace_box = st.empty()
            progress = st.progress(0, text="Preparing ingestion...")
            try:
                # Animate the visible backend workflow before the blocking ingestion call.
                # This mirrors what _run_ingestion performs internally and then the final card uses actual returned metrics.
                for i, (title, _) in enumerate(INGEST_STEPS[:5]):
                    progress.progress(int((i + 1) / 6 * 82), text=title)
                    trace_box.markdown(render_timeline(INGEST_STEPS, active=i, done=i - 1), unsafe_allow_html=True)
                    time.sleep(0.18)

                ingest_result = run_async(
                    ingest_uploaded_file(uploaded, access_level, chunk_strategy, chunk_size, chunk_overlap)
                )
                payload = ingest_result.model_dump() if hasattr(ingest_result, "model_dump") else dict(ingest_result)
                payload["mode"] = mode
                payload["index_path"] = index_path if mode == "local" else "Azure AI Search"
                st.session_state.last_ingest = payload
                st.session_state.ingest_trace = [
                    {"step": "Upload received", "summary": f"Received `{uploaded.name}` from the dashboard."},
                    {"step": "Text extraction", "summary": "Loaded document text and preserved file metadata."},
                    {"step": "Chunking", "summary": f"Used `{payload.get('strategy_used')}` chunking and created {payload.get('chunks_indexed')} searchable chunks."},
                    {"step": "Embedding", "summary": "Generated local deterministic embeddings in demo mode or Azure embeddings in production mode."},
                    {"step": "Index write", "summary": f"Saved chunks into `{payload.get('index_path')}` with access level `{payload.get('access_level')}`."},
                    {"step": "Ready", "summary": f"Indexing completed in {payload.get('elapsed_ms')} ms."},
                ]
                get_local_index_stats.clear()
                progress.progress(100, text="Document indexed")
                trace_box.markdown(render_timeline(INGEST_STEPS, active=-1, done=len(INGEST_STEPS) - 1), unsafe_allow_html=True)
                st.success(f"Indexed {payload.get('chunks_indexed')} chunks from {uploaded.name}")
                time.sleep(0.5)
                st.rerun()
            except Exception as exc:
                progress.empty()
                trace_box.empty()
                st.error(f"Ingestion failed: {exc}")

    with right:
        st.markdown("<div class='fq-card'><h3>📈 Knowledge base status</h3>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="fq-kpi-grid">
              <div class="fq-kpi"><div class="label">Indexed chunks</div><div class="value">{chunk_count}</div></div>
              <div class="fq-kpi"><div class="label">Indexed docs</div><div class="value">{doc_count}</div></div>
              <div class="fq-kpi"><div class="label">Runtime</div><div class="value">{html_escape(mode).upper()}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.last_ingest:
            ing = st.session_state.last_ingest
            st.markdown("#### ✅ Last upload summary")
            st.markdown(
                f"""
                <div class="fq-source">
                  <div class="fq-source-title">{html_escape(ing.get('filename'))}</div>
                  <div class="fq-source-meta">{ing.get('chunks_indexed')} chunks · {html_escape(ing.get('strategy_used'))} chunking · {html_escape(ing.get('access_level'))} access · {ing.get('elapsed_ms')} ms</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Show GPT-style backend summary", expanded=True):
                for item in st.session_state.ingest_trace or []:
                    st.markdown(f"**{item['step']}** — {item['summary']}")
        else:
            st.info("No upload completed in this session yet. Upload a document to see a backend summary here.")
        st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Ask/query tab
# ──────────────────────────────────────────────────────────────────────────────
with ask_tab:
    if chunk_count == 0:
        st.markdown(
            """
            <div class="fq-warning">
              <strong>No documents indexed yet.</strong> Open the <strong>Upload & Index</strong> tab and upload <span class="fq-code">sample_data/local_demo.md</span> or your own document first.
            </div>
            """,
            unsafe_allow_html=True,
        )

    qcol, hintcol = st.columns([1.25, 0.75], gap="large")
    with qcol:
        st.markdown("<div class='fq-panel'><div class='fq-section-title'>Ask the engineering knowledge base</div><div class='fq-muted'>The UI will show the backend pipeline live, then summarize what happened like an AI reasoning trace.</div></div>", unsafe_allow_html=True)
        query = st.text_area("Question", placeholder="Example: What does local demo mode demonstrate?", height=110)
        run_btn = st.button("▶ Run 5-agent pipeline", type="primary", use_container_width=True)
    with hintcol:
        st.markdown(
            f"""
            <div class="fq-card">
              <h3>Current access</h3>
              <div class="fq-muted">Role: <strong>{html_escape(role)}</strong></div>
              <div class="fq-muted">Top-k: <strong>{top_k}</strong> chunks</div>
              <div class="fq-muted">Mode: <strong>{html_escape(mode)}</strong></div>
              <br/>
              <div class="fq-small">Try switching roles to show how RBAC changes retrieved evidence.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if run_btn and query.strip():
        progress = st.progress(0, text="Starting FabIQ pipeline...")
        trace_box = st.empty()
        try:
            from fabiq.pipeline.graph import compile_pipeline

            for i, (title, _) in enumerate(PIPELINE_STEPS):
                progress.progress(int((i + 1) / 5 * 86), text=title)
                trace_box.markdown(
                    render_process_board(
                        PIPELINE_STEPS,
                        active=i,
                        done=i - 1,
                        title="FabIQ is processing your question",
                        subtitle="Each card lights up as the backend moves through the retrieval and answer pipeline.",
                    ),
                    unsafe_allow_html=True,
                )
                time.sleep(0.34)

            pipeline = compile_pipeline()
            initial_state = {
                "query": query.strip(),
                "user_role": role,
                "top_k": top_k,
                "session_id": f"dash-{int(time.time())}",
                "latency_ms": {},
                "errors": [],
            }
            result = run_async(pipeline.ainvoke(initial_state))
            progress.progress(100, text="Pipeline complete")
            trace_box.markdown(
                render_process_board(
                    PIPELINE_STEPS,
                    active=-1,
                    done=len(PIPELINE_STEPS) - 1,
                    title="FabIQ completed the backend pipeline",
                    subtitle="The answer is ready. The cards below show the completed process.",
                ),
                unsafe_allow_html=True,
            )
            time.sleep(0.35)
            progress.empty()
            trace_box.empty()

            chunks = result.get("retrieved_chunks", []) or []
            citations = result.get("citations", []) or []
            st.session_state.pipeline_trace = [
                {"step": "Query understanding", "summary": f"FabIQ understood this as a {result.get('query_intent', 'factual')} question and identified the important terms: {', '.join(result.get('query_entities', [])[:5]) or 'none detected'}."},
                {"step": "Privilege check", "summary": f"The selected role, {role}, was checked before retrieval so only allowed source material could be used."},
                {"step": "Hybrid retrieval", "summary": f"FabIQ searched the knowledge index and selected {len(chunks)} relevant source chunks. Best retrieval score: {result.get('retrieval_precision', 0):.3f}."},
                {"step": "Citation grounding", "summary": f"The response was built from retrieved evidence and connected to {len(citations)} cited source(s)."},
                {"step": "Quality evaluation", "summary": f"The answer received a confidence score of {result.get('eval_confidence', 0):.2f}. Human review needed: {'yes' if result.get('requires_human_review', False) else 'no'}."},
            ]
            st.session_state.last_result = result
            st.session_state.history.insert(
                0,
                {
                    "query": query.strip(),
                    "role": role,
                    "confidence": result.get("eval_confidence", 0),
                    "hitl": result.get("requires_human_review", False),
                },
            )
            st.session_state.history = st.session_state.history[:10]
            st.rerun()
        except Exception as exc:
            progress.empty()
            trace_box.empty()
            st.error(f"Pipeline error: {exc}")
            if mode == "local":
                st.info("Make sure at least one document is indexed. Use the Upload & Index tab first.")
            else:
                st.info("Azure mode requires valid Azure OpenAI and Azure AI Search credentials in `.env`.")
    elif run_btn and not query.strip():
        st.warning("Please enter a question first.")

    result = st.session_state.last_result
    if result:
        st.markdown("---")
        st.markdown(f"<div class='fq-chat-user'>{html_escape(result.get('query', query if 'query' in locals() else 'Question'))}</div>", unsafe_allow_html=True)
        st.markdown("<div class='fq-chat-assistant'><div class='fq-chat-label'>FabIQ answer</div>", unsafe_allow_html=True)
        st.markdown(result.get("response", "_No response generated_"))
        st.markdown("</div>", unsafe_allow_html=True)

        if result.get("requires_human_review"):
            st.markdown(
                f"""
                <div class="fq-warning">⚠️ <strong>Human review recommended.</strong> Confidence score {result.get('eval_confidence', 0):.2f} is below the configured threshold.</div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("🧠 What happened behind the scenes", expanded=True):
            st.markdown(
                render_process_board(
                    PIPELINE_STEPS,
                    active=-1,
                    done=len(PIPELINE_STEPS) - 1,
                    summaries=st.session_state.pipeline_trace,
                    title="Prompt processing summary",
                    subtitle="A simple, user-facing view of what happened after the prompt was submitted.",
                ),
                unsafe_allow_html=True,
            )

        citations = result.get("citations", [])
        if citations:
            st.markdown("### 📚 Evidence used")
            retrieved_by_id = {c.get("chunk_id"): c for c in (result.get("retrieved_chunks", []) or [])}
            for c in citations:
                source_name = pretty_source(c.get("source", "unknown"))
                page = f" · page {c['page_number']}" if c.get("page_number") else ""
                score = f" · score {c.get('score', 0):.3f}" if c.get("score") else ""
                chunk = retrieved_by_id.get(c.get("chunk_id"), {})
                st.markdown(
                    f"""
                    <div class="fq-source">
                      <div class="fq-source-title">[SOURCE_{c.get('source_num')}] {html_escape(source_name)}</div>
                      <div class="fq-source-meta">Chunk: {html_escape(c.get('chunk_id', 'unknown'))}{page}{score}</div>
                      <div class="fq-source-snippet">{html_escape(short(chunk.get('content', ''), 260))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("### 📊 Pipeline dashboard")
        col1, col2, col3 = st.columns([1, 1.15, 1], gap="large")
        with col1:
            st.markdown("<div class='fq-card'><h3>Quality</h3>", unsafe_allow_html=True)
            st.metric("Accuracy", f"{result.get('eval_accuracy', 0):.2f}")
            st.metric("Grounding", f"{result.get('eval_grounding', 0):.2f}")
            st.metric("Completeness", f"{result.get('eval_completeness', 0):.2f}")
            st.metric("Confidence", f"{result.get('eval_confidence', 0):.2f}", delta="Ready" if not result.get("requires_human_review") else "Review")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='fq-card'><h3>Agent latency</h3>", unsafe_allow_html=True)
            latency = result.get("latency_ms", {}) or {}
            agent_labels = {
                "agent_1_query_understanding": "Query understanding",
                "agent_2_privilege_check": "Privilege check",
                "agent_3_retrieval": "Hybrid retrieval",
                "agent_4_generation": "Citation grounding",
                "agent_5_eval_judge": "Quality eval",
            }
            max_ms = max([float(v or 0) for v in latency.values()] + [1.0])
            total_ms = 0.0
            for key, label in agent_labels.items():
                ms = float(latency.get(key, 0) or 0)
                total_ms += ms
                pct = max(4, min(100, int((ms / max_ms) * 100)))
                st.markdown(
                    f"""
                    <div class="fq-latency-row">
                      <span>{html_escape(label)}</span>
                      <span style="display:flex;align-items:center;gap:10px;"><span class="fq-bar"><span class="fq-fill" style="width:{pct}%"></span></span><code>{ms:.0f} ms</code></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown(f"**Total:** {total_ms:.0f} ms")
            st.markdown("</div>", unsafe_allow_html=True)
        with col3:
            chunks = result.get("retrieved_chunks", []) or []
            st.markdown("<div class='fq-card'><h3>State</h3>", unsafe_allow_html=True)
            st.metric("Chunks retrieved", len(chunks))
            st.metric("Retrieval score", f"{result.get('retrieval_precision', 0):.3f}")
            st.metric("Tokens used", result.get("tokens_used", "n/a"))
            st.metric("Intent", result.get("query_intent", "—"))
            if result.get("ungrounded_claims"):
                st.warning(f"{len(result['ungrounded_claims'])} ungrounded claim(s) detected")
            st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Backend process/explain tab
# ──────────────────────────────────────────────────────────────────────────────
with explain_tab:
    st.markdown(
        """
        <div class='fq-panel'>
          <div class='fq-section-title'>Backend process shown to the user</div>
          <div class='fq-muted'>When a user enters a prompt, FabIQ shows this five-step animated process. No code, keys, or technical internals are displayed — only a clear explanation of what is happening.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        render_process_board(
            PIPELINE_STEPS,
            active=-1,
            done=-1,
            title="The 5-step prompt journey",
            subtitle="This is the clean process view users see while their question is being handled.",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='fq-panel'>
          <div class='fq-section-title'>What the user understands</div>
          <div class='fq-muted'>The interface explains that FabIQ understands the question, checks access, retrieves evidence, creates a cited answer, and evaluates the response quality. The user sees progress and a plain-English summary instead of backend code.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────────────────────────────────────
# History
# ──────────────────────────────────────────────────────────────────────────────
if st.session_state.history:
    with st.expander(f"🕘 Query history ({len(st.session_state.history)} recent)"):
        for h in st.session_state.history:
            hitl_flag = "⚠ Review" if h["hitl"] else "✓ Ready"
            st.caption(f"[{h['role']}] {h['query'][:90]} · confidence {h['confidence']:.2f} · {hitl_flag}")
