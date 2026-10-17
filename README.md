# 🛡️ CloudGuard — GCP Misconfiguration Scanner

CloudGuard is a mini cloud-security scanner for Google Cloud Platform. It scans a GCP
project for common security misconfigurations, assigns severity levels, suggests
fixes, and produces a consolidated security scorecard — viewable either in the
terminal or through a Streamlit dashboard.

This project was built as a hands-on way to learn practical GCP security concepts
(IAM, least-privilege, audit logging, firewall exposure) beyond a course curriculum.

## What it checks

| Scanner | File | What it looks for |
|---|---|---|
| Storage Buckets | `bucket_scanner.py` | Buckets exposed to `allUsers` / `allAuthenticatedUsers` |
| IAM | `iam_scanner.py` | Members with broad `Owner`/`Editor` roles, and use of Google's auto-created default service account |
| Audit Logging | `logging_scanner.py` | Missing custom log sinks, short log retention on the default log bucket |
| Firewall | `firewall_scanner.py` | Ingress rules open to `0.0.0.0/0` on sensitive ports (SSH, RDP, databases, etc.) |

Each finding includes a **severity** (`CRITICAL` / `HIGH` / `MEDIUM` / `LOW`) and a
**suggested fix**. `scorecard.py` combines all four scanners and calculates a
0–100 security score by deducting points per finding.

## Architecture

```
bucket_scanner.py   ─┐
iam_scanner.py       ├─► scorecard.py ─► dashboard.py (Streamlit UI)
logging_scanner.py   │        └────────► terminal output (python scorecard.py)
firewall_scanner.py ─┘
```

Each scanner is a standalone module exposing a `scan_*()` function that returns a
list of findings (same shape across all scanners), so they can be run individually
or combined by `scorecard.py`.

## Prerequisites

- Python 3.9+
- A GCP project you have access to
- `gcloud` CLI installed and authenticated ([install guide](https://cloud.google.com/sdk/docs/install))
- A GCP billing account linked to the project (required for some APIs to activate — scanning itself costs effectively $0, these are read-only calls)

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/KeeratMalhotra/CloudGuard.git
cd CloudGuard
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Enable the required GCP APIs

```bash
gcloud services enable storage.googleapis.com iam.googleapis.com logging.googleapis.com cloudresourcemanager.googleapis.com compute.googleapis.com --project=YOUR_PROJECT_ID
```

### 3. Create a dedicated, read-only service account

CloudGuard is designed to run with a scoped-down, read-only identity — never your
personal admin credentials.

```bash
gcloud iam service-accounts create cloudguard-scanner --display-name="CloudGuard Scanner" --project=YOUR_PROJECT_ID
```

Create two custom roles with the minimum permissions the scanners need:

```bash
gcloud iam roles create cloudguardStorageReader --project=YOUR_PROJECT_ID \
  --title="CloudGuard Storage Reader" \
  --description="Read-only access to list buckets and view their IAM policies" \
  --permissions="storage.buckets.list,storage.buckets.get,storage.buckets.getIamPolicy" \
  --stage=GA

gcloud iam roles create cloudguardComputeReader --project=YOUR_PROJECT_ID \
  --title="CloudGuard Compute Reader" \
  --description="Read-only access to firewall rules and networks" \
  --permissions="compute.firewalls.list,compute.firewalls.get,compute.networks.list" \
  --stage=GA
```

Grant the service account the roles it needs (custom roles above, plus built-in
`Viewer` for general read access and `Logs Viewer` for the logging checks):

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudguard-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/viewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudguard-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="projects/YOUR_PROJECT_ID/roles/cloudguardStorageReader"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cloudguard-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="projects/YOUR_PROJECT_ID/roles/cloudguardComputeReader"
```

Generate a key file for this service account (keep it out of source control —
this repo's `.gitignore` already excludes `*.json` and `credentials/`):

```bash
mkdir credentials
gcloud iam service-accounts keys create credentials/cloudguard-key.json \
  --iam-account=cloudguard-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 4. Set environment variables

```bash
# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\CloudGuard\credentials\cloudguard-key.json"
$env:CLOUDGUARD_PROJECT_ID = "YOUR_PROJECT_ID"

# macOS/Linux
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/CloudGuard/credentials/cloudguard-key.json"
export CLOUDGUARD_PROJECT_ID="YOUR_PROJECT_ID"
```

`CLOUDGUARD_PROJECT_ID` is optional for the dashboard (you can type the project ID
directly into the UI instead), but required for the terminal scripts below.

## Usage

**Run an individual scanner:**
```bash
python bucket_scanner.py
python iam_scanner.py
python logging_scanner.py
python firewall_scanner.py
```

**Run the full consolidated scorecard (terminal):**
```bash
python scorecard.py
```

**Run the Streamlit dashboard:**
```bash
streamlit run dashboard.py
```
Opens at `http://localhost:8501`. Enter a GCP project ID and click **Run Security Scan**.

## Scoring model

Score starts at 100 and deducts points per finding:

| Severity | Points deducted |
|---|---|
| CRITICAL | -20 |
| HIGH | -10 |
| MEDIUM | -5 |
| LOW | -2 |

| Score | Grade |
|---|---|
| 90–100 | Excellent |
| 70–89 | Good |
| 50–69 | Needs Improvement |
| < 50 | Critical Risk |

## Security notes

- This tool is intentionally **read-only** — none of the scanners can modify,
  create, or delete any GCP resource. The custom IAM roles above grant only
  `list`/`get`/`getIamPolicy` permissions.
- Never commit the service account key JSON file. `.gitignore` is configured to
  exclude `credentials/` and `*.json` by default.
- Run the scanner with a dedicated, scoped-down service account rather than your
  personal/admin credentials (principle of least privilege).

## Possible future additions

- Cloud SQL / BigQuery public exposure checks
- Service account key age/rotation checks
- CIS GCP Foundation Benchmark control mapping
- Scan history + trend tracking over time
- Multi-project / organization-wide scanning
