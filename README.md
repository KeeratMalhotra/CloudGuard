# CloudGuard — GCP Misconfiguration Scanner

CloudGuard scans a Google Cloud project for common security misconfigurations,
scores the project from 0-100, and suggests fixes. It checks public storage
buckets, over-privileged IAM roles, audit logging gaps, and firewall rules
open to the internet.

A landing page for this project lives in `landing/` and can be deployed
separately (e.g. on Vercel).

## What it checks

| Scanner | File | Looks for |
|---|---|---|
| Storage Buckets | `bucket_scanner.py` | Buckets exposed to `allUsers` / `allAuthenticatedUsers` |
| IAM | `iam_scanner.py` | Broad `Owner`/`Editor` roles, and Google's default service account |
| Audit Logging | `logging_scanner.py` | Missing log sinks, short log retention |
| Firewall | `firewall_scanner.py` | Ingress rules open to `0.0.0.0/0` on sensitive ports |

Every scanner returns a list of findings in the same shape:
`scanner`, `severity`, `resource`, `description`, `fix`. `scorecard.py`
combines all four lists and calculates a score by deducting points per
finding.

## How it works

```
bucket_scanner.py   ─┐
iam_scanner.py       ├─► scorecard.py ─► dashboard.py (Streamlit UI)
logging_scanner.py   │        └────────► terminal output (python scorecard.py)
firewall_scanner.py ─┘
```

## Setup

### 1. Get the code

```bash
git clone https://github.com/KeeratMalhotra/CloudGuard.git
cd CloudGuard
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Enable the required GCP APIs

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable storage.googleapis.com iam.googleapis.com logging.googleapis.com cloudresourcemanager.googleapis.com compute.googleapis.com
```

### 4. Create a read-only service account

CloudGuard runs as its own service account, not as you. The basic `Viewer`
role doesn't cover reading a bucket's IAM policy, so two custom roles fill
that gap.

```bash
gcloud iam service-accounts create cloudguard-scanner --display-name="CloudGuard Scanner"

gcloud iam roles create cloudguardStorageReader --project=YOUR_PROJECT_ID \
  --title="CloudGuard Storage Reader" \
  --permissions="storage.buckets.list,storage.buckets.get,storage.buckets.getIamPolicy" \
  --stage=GA

gcloud iam roles create cloudguardComputeReader --project=YOUR_PROJECT_ID \
  --title="CloudGuard Compute Reader" \
  --permissions="compute.firewalls.list,compute.firewalls.get,compute.networks.list" \
  --stage=GA

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

Note (Windows PowerShell): keep the quotes around `--permissions`. Without
them, PowerShell splits the comma-separated list and `gcloud` rejects it.

### 5. Generate a key and create `.env`

```bash
mkdir credentials
gcloud iam service-accounts keys create credentials/cloudguard-key.json \
  --iam-account=cloudguard-scanner@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

Create a file named `.env` in the project root:

```
PROJ_ID=YOUR_PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/CloudGuard/credentials/cloudguard-key.json
```

The code never reads this key file directly. Google's client libraries read
`GOOGLE_APPLICATION_CREDENTIALS` automatically when a client is created
(Application Default Credentials).

`credentials/`, `*.json`, and `.env` are already in `.gitignore`, so the key
never gets committed.

## Usage

Run one scanner on its own:

```bash
python bucket_scanner.py
python iam_scanner.py
python logging_scanner.py
python firewall_scanner.py
```

Run all four and print a combined scorecard:

```bash
python scorecard.py
```

Run the dashboard:

```bash
streamlit run dashboard.py
```

Opens at `http://localhost:8501`.

## Scoring

Score starts at 100 and loses points per finding:

| Severity | Points lost |
|---|---|
| CRITICAL | 20 |
| HIGH | 10 |
| MEDIUM | 5 |
| LOW | 2 |

| Score | Grade |
|---|---|
| 90-100 | Excellent |
| 70-89 | Good |
| 50-69 | Needs improvement |
| 0-49 | Critical risk |

## Troubleshooting

**`403 ... does not have storage.buckets.getIamPolicy access`**
The service account only has `roles/viewer`, which doesn't cover reading a
bucket's IAM policy. Bind the `cloudguardStorageReader` custom role from
setup step 4.

**`API has not been used in project <some other project>`**
Credentials didn't load, so Google fell back to an older login on your
machine. Check that `GOOGLE_APPLICATION_CREDENTIALS` is set in `.env` and
points to the real key file.

**`Scanning project 'None'` or `Required parameter: project`**
`PROJ_ID` is missing from `.env`, or the script isn't being run from the
folder that contains `.env`.

**`The billing account for the owning project is disabled`**
Some APIs require a billing account linked to the project, even if nothing
is spent. Link one under Billing, then Link a billing account.

## Security notes

- The scanner is read-only. It can list and read configuration, not create,
  modify, or delete anything.
- The two custom roles grant only six permissions total - the minimum the
  scanners need.
- Secrets (`credentials/`, `*.json`, `.env`) are git-ignored from the start.
- The scanner reads policies and settings, never the contents of your
  buckets.

## Possible additions

- Cloud SQL / BigQuery public exposure checks
- Service account key age checks
- CIS GCP Foundation Benchmark mapping
- Scan history and trend tracking
- Multi-project scanning
