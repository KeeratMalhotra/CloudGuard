import os
from google.cloud import resourcemanager_v3

PROJECT_ID = os.environ.get("CLOUDGUARD_PROJECT_ID", "cloudguard-scan-002")
RISKY_ROLES = ["roles/owner", "roles/editor"]

def is_default_service_account(member):
    return (
        "-compute@developer.gserviceaccount.com" in member
        or "@appspot.gserviceaccount.com" in member
    )

def scan_iam(project_id=PROJECT_ID):
    client = resourcemanager_v3.ProjectsClient()
    resource = f"projects/{project_id}"
    policy = client.get_iam_policy(resource=resource)

    findings = []
    for binding in policy.bindings:
        role = binding.role
        for member in binding.members:
            if is_default_service_account(member):
                findings.append({
                    "scanner": "IAM",
                    "severity": "HIGH",
                    "resource": member,
                    "description": f"Default service account has role '{role}'",
                    "fix": "Avoid using Google's auto-created default service account. "
                           "Create a dedicated service account with only the permissions it needs.",
                })
            elif role in RISKY_ROLES:
                findings.append({
                    "scanner": "IAM",
                    "severity": "MEDIUM",
                    "resource": member,
                    "description": f"Member has broad role '{role}'",
                    "fix": "Review whether this member truly needs Owner/Editor. "
                           "Prefer narrower, specific roles (principle of least privilege).",
                })

    return findings

if __name__ == "__main__":
    print(f"Scanning IAM policy for project '{PROJECT_ID}'...")
    results = scan_iam()
    if not results:
        print("○ No risky IAM assignments found.")
    else:
        print(f"● Found {len(results)} finding(s):")
        for f in results:
            print(f"  -> [{f['severity']}] {f['resource']}: {f['description']}")
            print(f"     FIX: {f['fix']}")
    print("Scan complete.")
