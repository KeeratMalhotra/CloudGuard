import csv
import io
import json
import os
import time
from datetime import datetime
from html import escape

import streamlit as st

from scorecard import (
    SEVERITY_ORDER,
    SEVERITY_WEIGHTS,
    calculate_score,
    grade_for_score,
    run_all_scans,
)

DEFAULT_PROJECT_ID = os.environ.get("PROJ_ID")

SEVERITY_COLORS = {
    "CRITICAL": "#E5675A",
    "HIGH": "#E9A15B",
    "MEDIUM": "#D6C26E",
    "LOW": "#7FA6D6",
}
SCANNERS = ["Storage Buckets", "IAM", "Audit Logging", "Firewall"]

st.set_page_config(page_title="CloudGuard", page_icon="🛡️", layout="wide")


# ---------------------------------------------------------------------------
# Styling: same palette and fonts as the landing page
# ---------------------------------------------------------------------------
def html(markup):
    """Render raw HTML. Lines are flattened so Markdown doesn't treat
    indented HTML as a code block."""
    # join with a space so attributes split across lines stay separated
    flat = " ".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(flat, unsafe_allow_html=True)


html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300..700&family=Geist+Mono:wght@400..600&family=Instrument+Serif:ital@0;1&display=swap');
:root {
  --cg-line: rgba(255,255,255,0.07);
  --cg-line-2: rgba(255,255,255,0.13);
  --cg-panel: #141416;
  --cg-panel-2: #18181b;
  --cg-muted: #A1A19C;
  --cg-dim: #6E6E69;
  --cg-accent: #D97757;
  --cg-sans: 'Geist', ui-sans-serif, system-ui, sans-serif;
  --cg-mono: 'Geist Mono', ui-monospace, Menlo, Consolas, monospace;
  --cg-serif: 'Instrument Serif', Georgia, serif;
}
.stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li { font-family: var(--cg-sans); }
.stApp code { font-family: var(--cg-mono); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #0F0F11; border-right: 1px solid var(--cg-line); }
.block-container { padding-top: 2.6rem; max-width: 1200px; }
[data-testid="stSidebar"] .stButton button { width: 100%; height: 44px; border-radius: 999px; font-weight: 500; }
.stDownloadButton button { border-radius: 999px; }

.cg-brand { display:flex; align-items:center; gap:10px; font-weight:600; font-size:17px; margin: 4px 0 26px; }
.cg-brand svg { width:22px; height:22px; color: var(--cg-accent); }
.cg-side-label { font-family: var(--cg-mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--cg-dim); margin: 22px 0 8px; }
.cg-status { display:flex; align-items:center; gap:8px; font-size:13px; color: var(--cg-muted); padding: 6px 0; }
.cg-status i { width:7px; height:7px; border-radius:50%; display:inline-block; }
.cg-side-note { font-size: 12.5px; color: var(--cg-dim); line-height: 1.55; margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--cg-line); }

.cg-kicker { font-family: var(--cg-mono); font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--cg-accent); margin-bottom: 6px; }
.cg-title { font-family: var(--cg-serif); font-weight: 400; font-size: 46px; line-height: 1.05; letter-spacing: -0.01em; margin: 0; }
.cg-title em { color: var(--cg-muted); }
.cg-meta { font-family: var(--cg-mono); font-size: 12.5px; color: var(--cg-dim); margin-top: 10px; }

.cg-card { border: 1px solid var(--cg-line); background: var(--cg-panel); border-radius: 14px; padding: 22px; height: 100%; }
.cg-label { font-family: var(--cg-mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--cg-dim); }

.cg-score { display:flex; align-items:center; gap: 22px; }
.cg-ring { position: relative; width: 132px; height: 132px; flex: none; }
.cg-ring svg { width:100%; height:100%; transform: rotate(-90deg); }
.cg-ring .track { fill:none; stroke: rgba(255,255,255,.07); stroke-width: 9; }
.cg-ring .bar { fill:none; stroke-width: 9; stroke-linecap: round; }
.cg-ring .val { position:absolute; inset:0; display:grid; place-content:center; text-align:center; }
.cg-ring .val b { font-family: var(--cg-serif); font-weight: 400; font-size: 44px; line-height: 1; }
.cg-ring .val small { font-family: var(--cg-mono); font-size: 11px; color: var(--cg-dim); }
.cg-grade { font-size: 22px; font-weight: 500; margin: 6px 0 4px; }
.cg-sub { color: var(--cg-muted); font-size: 13.5px; line-height: 1.5; }

.cg-sev-grid { display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; height: 100%; }
.cg-sev { border: 1px solid var(--cg-line); background: var(--cg-panel); border-radius: 14px; padding: 18px; position: relative; overflow: hidden; }
.cg-sev::before { content:""; position:absolute; left:0; top:0; bottom:0; width:2px; background: var(--c); opacity:.9; }
.cg-sev b { display:block; font-family: var(--cg-serif); font-weight: 400; font-size: 42px; line-height: 1.1; margin-top: 10px; }
.cg-sev span.w { font-family: var(--cg-mono); font-size: 11.5px; color: var(--cg-dim); }

.cg-scan-grid { display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 14px 0 6px; }
.cg-scan { border: 1px solid var(--cg-line); background: var(--cg-panel); border-radius: 12px; padding: 14px 16px; display:flex; justify-content: space-between; align-items: center; }
.cg-scan .n { font-size: 14px; }
.cg-scan .c { font-family: var(--cg-mono); font-size: 13px; color: var(--cg-muted); display:flex; align-items:center; gap:8px; }
.cg-scan .c i { width:7px; height:7px; border-radius:50%; display:inline-block; }

.cg-section { display:flex; align-items: baseline; justify-content: space-between; margin: 34px 0 10px; }
.cg-section h3 { font-family: var(--cg-serif); font-weight: 400; font-size: 30px; margin: 0; }
.cg-section span { font-family: var(--cg-mono); font-size: 12px; color: var(--cg-dim); }

.cg-chip { display:inline-flex; align-items:center; height: 22px; padding: 0 8px; border-radius: 6px; font-family: var(--cg-mono); font-size: 11px; letter-spacing: .04em; border: 1px solid var(--c); color: var(--c); background: color-mix(in srgb, var(--c) 10%, transparent); }
.cg-finding { border: 1px solid var(--cg-line); background: var(--cg-panel); border-radius: 12px; padding: 16px 18px; margin-bottom: 10px; display: grid; grid-template-columns: 110px 1fr; gap: 14px; }
.cg-finding:hover { border-color: var(--cg-line-2); }
.cg-finding .src { font-family: var(--cg-mono); font-size: 11px; color: var(--cg-dim); margin-top: 8px; }
.cg-finding .desc { font-size: 15px; font-weight: 500; margin-bottom: 6px; }
.cg-finding .res { font-family: var(--cg-mono); font-size: 12.5px; color: #CFCFCA; background: rgba(255,255,255,.04); border: 1px solid var(--cg-line); border-radius: 6px; padding: 2px 8px; display: inline-block; margin-bottom: 10px; word-break: break-all; }
.cg-finding .fix { font-size: 13.5px; color: var(--cg-muted); }
.cg-finding .fix b { color: #E8936F; font-weight: 500; }

.cg-empty { border: 1px dashed var(--cg-line-2); border-radius: 16px; padding: 56px 32px; text-align: center; margin-top: 28px; }
.cg-empty h3 { font-family: var(--cg-serif); font-weight: 400; font-size: 34px; margin: 0 0 10px; }
.cg-empty p { color: var(--cg-muted); max-width: 520px; margin: 0 auto; }
.cg-checks { display:flex; justify-content:center; gap: 10px; flex-wrap: wrap; margin-top: 24px; }
.cg-checks span { font-family: var(--cg-mono); font-size: 12px; color: var(--cg-muted); border: 1px solid var(--cg-line-2); border-radius: 999px; padding: 6px 12px; }

@media (max-width: 900px) {
  .cg-sev-grid, .cg-scan-grid { grid-template-columns: repeat(2, 1fr); }
  .cg-finding { grid-template-columns: 1fr; }
}
</style>
""")

SHIELD_SVG = (
    '<svg viewBox="0 0 32 32" fill="none">'
    '<path d="M16 4.5 26 8.4v7.3c0 6-4.1 10.6-10 12.2-5.9-1.6-10-6.2-10-12.2V8.4l10-3.9Z" '
    'stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'
    '<path d="m11.8 16.2 2.9 2.9 5.5-5.7" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def grade_color(score):
    if score >= 90:
        return SEVERITY_COLORS["LOW"]
    if score >= 70:
        return SEVERITY_COLORS["MEDIUM"]
    if score >= 50:
        return SEVERITY_COLORS["HIGH"]
    return SEVERITY_COLORS["CRITICAL"]


def findings_to_csv(findings):
    buffer = io.StringIO()
    fields = ["severity", "scanner", "resource", "description", "fix"]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(findings)
    return buffer.getvalue()


def run_scan(project_id):
    """Runs the scan and stores the result in session_state.

    Streamlit re-runs this whole file on every click or filter change, so
    the results have to live in session_state or they'd vanish (and the
    scan would hit the GCP APIs again) every time someone touches a filter.
    """
    started = time.perf_counter()
    try:
        findings = run_all_scans(project_id)
    except Exception as e:  # show the real reason, but keep the UI alive
        st.session_state.scan = None
        st.session_state.scan_error = str(e)
        return

    order = {sev: i for i, sev in enumerate(SEVERITY_ORDER)}
    findings.sort(key=lambda f: order.get(f["severity"], len(order)))
    score = calculate_score(findings)
    st.session_state.scan_error = None
    st.session_state.scan = {
        "project_id": project_id,
        "findings": findings,
        "score": score,
        "grade": grade_for_score(score),
        "scanned_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        "duration": time.perf_counter() - started,
    }


st.session_state.setdefault("scan", None)
st.session_state.setdefault("scan_error", None)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    html(f'<div class="cg-brand">{SHIELD_SVG}<span>CloudGuard</span></div>')

    html('<div class="cg-side-label">Project</div>')
    project_id = st.text_input(
        "GCP project ID",
        value=DEFAULT_PROJECT_ID,
        placeholder="my-gcp-project-123",
        label_visibility="collapsed",
    ).strip()

    if st.button("Run security scan", type="primary", disabled=not project_id):
        with st.spinner("Scanning buckets, IAM, logging and firewall rules…"):
            run_scan(project_id)

    has_creds = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    html('<div class="cg-side-label">Environment</div>')
    html(
        f'<div class="cg-status"><i style="background:{"#7FB685" if has_creds else "#E5675A"}"></i>'
        f'Service account key {"detected" if has_creds else "not set"}</div>'
        f'<div class="cg-status"><i style="background:{"#7FB685" if DEFAULT_PROJECT_ID else "#6E6E69"}"></i>'
        f'PROJ_ID {"loaded from .env" if DEFAULT_PROJECT_ID else "not in .env"}</div>'
    )
    html(
        '<div class="cg-side-note">Read-only scan. CloudGuard reads policies, rules and '
        'settings through your scanner service account. Nothing is changed in your project.</div>'
    )


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
scan = st.session_state.scan

if st.session_state.scan_error:
    st.error(
        "**Scan failed.** Check that the project ID is correct, "
        "`GOOGLE_APPLICATION_CREDENTIALS` points to your key file, the APIs are "
        "enabled, and the service account has its read-only roles.\n\n"
        f"`{st.session_state.scan_error}`"
    )

if scan is None:
    html("""
    <div class="cg-kicker">Security posture</div>
    <h1 class="cg-title">Scan a project <em>to see its score.</em></h1>
    <div class="cg-empty">
      <h3>Nothing scanned yet</h3>
      <p>Enter a GCP project ID in the sidebar and run a scan. CloudGuard checks four
      areas and scores the project from 0 to 100.</p>
      <div class="cg-checks">
        <span>Public buckets</span><span>Over-privileged IAM</span>
        <span>Audit logging</span><span>Exposed firewall ports</span>
      </div>
    </div>
    """)
    st.stop()

findings = scan["findings"]
score = scan["score"]
counts = {sev: sum(1 for f in findings if f["severity"] == sev) for sev in SEVERITY_ORDER}

# Header
html(
    f'<div class="cg-kicker">Security posture</div>'
    f'<h1 class="cg-title">{escape(scan["project_id"])}</h1>'
    f'<div class="cg-meta">Scanned {scan["scanned_at"]} · {scan["duration"]:.1f}s · '
    f'{len(findings)} finding{"s" if len(findings) != 1 else ""}</div>'
)
st.write("")

# Score ring + severity summary
circumference = 2 * 3.14159 * 52
offset = circumference * (1 - score / 100)
color = grade_color(score)

col_score, col_sev = st.columns([1, 1.9], gap="medium")
with col_score:
    html(f"""
    <div class="cg-card">
      <div class="cg-label">Security score</div>
      <div class="cg-score" style="margin-top:14px">
        <div class="cg-ring">
          <svg viewBox="0 0 120 120">
            <circle class="track" cx="60" cy="60" r="52"/>
            <circle class="bar" cx="60" cy="60" r="52" stroke="{color}"
              stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}"/>
          </svg>
          <div class="val"><b>{score}</b><small>/100</small></div>
        </div>
        <div>
          <div class="cg-grade" style="color:{color}">{escape(scan["grade"])}</div>
          <div class="cg-sub">Starts at 100, minus each finding's severity weight.</div>
        </div>
      </div>
    </div>
    """)

with col_sev:
    cards = "".join(
        f'<div class="cg-sev" style="--c:{SEVERITY_COLORS[sev]}">'
        f'<div class="cg-label" style="color:{SEVERITY_COLORS[sev]}">{sev}</div>'
        f'<b>{counts[sev]}</b><span class="w">−{SEVERITY_WEIGHTS[sev]} pts each</span></div>'
        for sev in SEVERITY_ORDER
    )
    html(f'<div class="cg-sev-grid">{cards}</div>')

# Per-scanner breakdown
scanner_cards = ""
for name in SCANNERS:
    hits = [f for f in findings if f["scanner"] == name]
    worst = next((sev for sev in SEVERITY_ORDER if any(f["severity"] == sev for f in hits)), None)
    dot = SEVERITY_COLORS[worst] if worst else "#7FB685"
    label = f"{len(hits)} issue{'s' if len(hits) != 1 else ''}" if hits else "clean"
    scanner_cards += (
        f'<div class="cg-scan"><span class="n">{name}</span>'
        f'<span class="c"><i style="background:{dot}"></i>{label}</span></div>'
    )
html(f'<div class="cg-scan-grid">{scanner_cards}</div>')

# Findings
if not findings:
    html("""
    <div class="cg-empty">
      <h3>No misconfigurations found</h3>
      <p>All four checks came back clean for this project.</p>
    </div>
    """)
    st.stop()

html(f'<div class="cg-section"><h3>Findings</h3><span>sorted by severity</span></div>')

f1, f2, f3 = st.columns([1.2, 1.2, 1.6])
with f1:
    sev_filter = st.multiselect("Severity", SEVERITY_ORDER, default=SEVERITY_ORDER)
with f2:
    present = [s for s in SCANNERS if any(f["scanner"] == s for f in findings)]
    scanner_filter = st.multiselect("Scanner", present, default=present)
with f3:
    query = st.text_input("Search", placeholder="resource, role, port…").strip().lower()

visible = [
    f for f in findings
    if f["severity"] in sev_filter
    and f["scanner"] in scanner_filter
    and (not query or query in " ".join(str(v) for v in f.values()).lower())
]

for f in visible:
    c = SEVERITY_COLORS.get(f["severity"], "#A1A19C")
    # Values come from the GCP API, so escape them before putting them in HTML
    html(f"""
    <div class="cg-finding">
      <div>
        <span class="cg-chip" style="--c:{c}">{escape(f["severity"])}</span>
        <div class="src">{escape(f["scanner"])}</div>
      </div>
      <div>
        <div class="desc">{escape(f["description"])}</div>
        <div class="res">{escape(str(f.get("resource", "")))}</div>
        <div class="fix"><b>Fix:</b> {escape(f["fix"])}</div>
      </div>
    </div>
    """)

if not visible:
    st.caption("No findings match these filters.")

# Export
st.write("")
d1, d2, _ = st.columns([1, 1, 3])
stamp = datetime.now().strftime("%Y%m%d-%H%M")
with d1:
    st.download_button(
        "Download CSV",
        findings_to_csv(findings),
        file_name=f"cloudguard-{scan['project_id']}-{stamp}.csv",
        mime="text/csv",
    )
with d2:
    st.download_button(
        "Download JSON",
        json.dumps({k: v for k, v in scan.items() if k != "duration"}, indent=2),
        file_name=f"cloudguard-{scan['project_id']}-{stamp}.json",
        mime="application/json",
    )
