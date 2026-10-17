import os
from google.cloud.logging_v2.services.config_service_v2 import ConfigServiceV2Client
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.environ.get("PROJ_ID")

def scan_logging(project_id):
    client = ConfigServiceV2Client()
    parent = f"projects/{project_id}"
    findings =[]

    sinks = list(client.list_sinks(parent=parent))
    custom_sinks = [s for s in sinks if not s.name.startswith("_")]#sinks starting with _ are default ones that already exists in the project

    if len(custom_sinks)==0:

        findings.append({
            "scanner": "Audit Logging",
            "severity": "MEDIUM",
            "resource": project_id,
            "description": "No custom log sinks configured - logs only live in the default bucket.",
            "fix": "Create a log sink to export logs to a separate bucket/BigQuery for "
                   "longer-term retention and tamper resistance.",
        })

    bucket_name = f"{parent}/locations/global/buckets/_Default"
    bucket = client.get_bucket(request={"name": bucket_name})

    if bucket.retention_days <= 30:
        findings.append({
            "scanner": "Audit Logging",
            "severity": "LOW",
            "resource": project_id,
            "description": f"Default log bucket retention is only {bucket.retention_days} days.",
            "fix": "Consider increasing retention (e.g. to 90+ days), or export logs via a sink.",
        })

    return findings

if __name__ == "__main__":

    print(f"Scanning Cloud Logging config for project '{PROJECT_ID}'...")
    results = scan_logging()

    if not results:
        print("Logging configuration looks good.")
    else:
        print(f"Found {len(results)} finding(s):")
        for f in results:
            print(f"-> [{f['severity']}] {f['description']}")
            print(f"FIX: {f['fix']}")

    print("Scan complete.")
