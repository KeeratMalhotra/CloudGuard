from google.cloud import storage

PROJECT_ID = "cloudguard-scan-002"
PUBLIC_IDENTIFIERS = ["allUsers", "allAuthenticatedUsers"]

def scan_buckets(project_id=PROJECT_ID):
    """Scans all buckets in the project for public access. Returns a list of findings."""
    client = storage.Client(project=project_id)
    buckets = list(client.list_buckets())
    findings = []

    for bucket in buckets:
        policy = client.bucket(bucket.name).get_iam_policy(requested_policy_version=3)
        exposed_members = set()
        for binding in policy.bindings:
            for member in binding["members"]:
                if member in PUBLIC_IDENTIFIERS:
                    exposed_members.add(member)

        if exposed_members:
            findings.append({
                "scanner": "Storage Buckets",
                "severity": "CRITICAL",
                "resource": bucket.name,
                "description": f"Bucket is publicly accessible to {', '.join(exposed_members)}",
                "fix": "Remove allUsers/allAuthenticatedUsers from the bucket's IAM policy, "
                       "or enable Public Access Prevention.",
            })

    return findings

if __name__ == "__main__":
    print(f"Scanning buckets in project '{PROJECT_ID}'...")
    results = scan_buckets()
    if not results:
        print("○ No public buckets found.")
    else:
        print(f"● Found {len(results)} finding(s):")
        for f in results:
            print(f"  -> [{f['severity']}] {f['resource']}: {f['description']}")
            print(f"     FIX: {f['fix']}")
    print("Scan complete.")
