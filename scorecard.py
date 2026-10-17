import os
from bucket_scanner import scan_buckets
from iam_scanner import scan_iam
from logging_scanner import scan_logging
from firewall_scanner import scan_firewalls
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.environ.get("PROJ_ID")

SEVERITY_WEIGHTS = {
    "CRITICAL": 20,
    "HIGH": 10,
    "MEDIUM": 5,
    "LOW": 2,
}

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

def run_all_scans(project_id=PROJECT_ID):
    """Runs every scanner and returns one combined list of findings."""
    all_findings = []
    all_findings += scan_buckets(project_id)
    all_findings += scan_iam(project_id)
    all_findings += scan_logging(project_id)
    all_findings += scan_firewalls(project_id)
    return all_findings

def calculate_score(findings):
    """Starts at 100, deducts points per finding based on severity."""
    score = 100
    for f in findings:
        score -= SEVERITY_WEIGHTS.get(f["severity"], 0)
    return max(score, 0)

def grade_for_score(score):
    if score >= 90:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Needs Improvement"
    else:
        return "Critical Risk"

def print_scorecard(project_id=PROJECT_ID):
    findings = run_all_scans(project_id)
    score = calculate_score(findings)
    grade = grade_for_score(score)

    print("=" * 60)
    print(f"  CLOUDGUARD SECURITY SCORECARD - {project_id}")
    print("=" * 60)
    print(f"SCORE: {score}/100   ({grade})")

    if not findings:
        print("  ○ No issues found. Great job!")
    else:
        # Group findings by severity for a cleaner report
        for severity in SEVERITY_ORDER:
            matching = [f for f in findings if f["severity"] == severity]
            if not matching:
                continue
            print(f"  --- {severity} ({len(matching)}) ---")
            for f in matching:
                print(f"  [{f['scanner']}] {f['resource']}")
                print(f"      Issue: {f['description']}")
                print(f"      Fix:   {f['fix']}")

    print("=" * 60)
    print(f"  Total findings: {len(findings)}")
    print("=" * 60)

if __name__ == "__main__":
    print_scorecard()
