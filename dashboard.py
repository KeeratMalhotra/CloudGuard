import os
import streamlit as st
from scorecard import run_all_scans, calculate_score, grade_for_score, SEVERITY_ORDER

DEFAULT_PROJECT_ID = os.environ.get("CLOUDGUARD_PROJECT_ID", "")

st.set_page_config(page_title="CloudGuard", page_icon="🛡️", layout="centered")

st.title("🛡️ CloudGuard")
st.caption("GCP Misconfiguration Scanner")

PROJECT_ID = st.text_input(
    "GCP Project ID to scan",
    value=DEFAULT_PROJECT_ID,
    placeholder="e.g. my-gcp-project-123",
    help="The scanner uses this project ID and your active credentials "
         "(GOOGLE_APPLICATION_CREDENTIALS) to run all checks.",
)

if st.button("Run Security Scan", type="primary", disabled=not PROJECT_ID):
    try:
        with st.spinner("Scanning project... this may take a few seconds"):
            findings = run_all_scans(PROJECT_ID)
            score = calculate_score(findings)
            grade = grade_for_score(score)
    except Exception as e:
        st.error(
            "Scan failed. Double-check that:\n"
            "- The project ID is correct\n"
            "- GOOGLE_APPLICATION_CREDENTIALS points to a valid service account key\n"
            "- The required APIs are enabled and the service account has the "
            "necessary read-only roles (see README.md)\n\n"
            f"Error details: {e}"
        )
        st.stop()

    # --- Scorecard header ---
    st.metric(label="Security Score", value=f"{score}/100", delta=grade)

    if score >= 90:
        st.success(f"Grade: {grade}")
    elif score >= 70:
        st.info(f"Grade: {grade}")
    elif score >= 50:
        st.warning(f"Grade: {grade}")
    else:
        st.error(f"Grade: {grade}")

    st.divider()

    if not findings:
        st.success("🎉 No issues found!")
    else:
        st.subheader(f"Findings ({len(findings)})")

        severity_colors = {
            "CRITICAL": "●",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "◦",
        }

        for severity in SEVERITY_ORDER:
            matching = [f for f in findings if f["severity"] == severity]
            if not matching:
                continue

            st.markdown(f"### {severity_colors[severity]} {severity} ({len(matching)})")
            for f in matching:
                with st.expander(f"[{f['scanner']}] {f['resource']}"):
                    st.write(f"**Issue:** {f['description']}")
                    st.write(f"**Fix:** {f['fix']}")
else:
    st.info("Click the button above to scan your GCP project for misconfigurations.")
