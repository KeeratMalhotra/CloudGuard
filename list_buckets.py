from google.cloud import storage

PROJECT_ID = "cloud-guard-511811"

def list_buckets():
    client = storage.Client(project=PROJECT_ID)
    buckets = list(client.list_buckets())

    if not buckets:
        print("No buckets found in this project.")
        return

    print(f"Found {len(buckets)} bucket(s):")
    for bucket in buckets:
        print(f" - {bucket.name}")

if __name__ == "__main__":
    list_buckets()
