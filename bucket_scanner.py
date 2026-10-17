import os
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()
PROJECT_ID = os.environ.get("PROJ_ID")

PUBLIC_IDENTIFIERS = ["allUsers", "allAuthenticatedUsers"]#these are the only 2 public identifiers mentioned in google cloud docs

def scan_buckets(project_id):
   #Scanning all buckets in the project for public access
    client = storage.Client(project_id)
    buckets = list(client.list_buckets())
    findings = []

    for bucket in buckets:
        policy = client.bucket(bucket.name).get_iam_policy(requested_policy_version=3)
        exposed_members = set()

        for binding in policy.bindings:
            for member in binding["members"]:
                if member in PUBLIC_IDENTIFIERS:
                    exposed_members.add(member)

        if len(exposed_members)>0 :
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

    print(f"Scanning the buckets in project '{PROJECT_ID}'...")
    results = scan_buckets(PROJECT_ID)

    if len(results)==0:
        print("No public buckets found.")
    else:
        print(f"Found {len(results)} finding(s):")
        for f in results:
            print(f"-> [{f['severity']}] {f['resource']}: {f['description']}")
            print(f"FIX: {f['fix']}")
            print()

    print("Scan complete")
