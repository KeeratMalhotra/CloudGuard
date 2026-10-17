import os
from google.cloud import compute_v1
from dotenv import load_dotenv

load_dotenv();
PROJECT_ID = os.environ.get("PROJ_ID")

RISKY_PORTS = {
    "22": "SSH", "3389": "RDP", "3306": "MySQL",
    "5432": "PostgreSQL", "27017": "MongoDB",
    "6379": "Redis", "9200": "Elasticsearch",
}
OPEN_TO_WORLD = "0.0.0.0/0"

def evaluate_rule(rule):
    findings = []

    if rule.direction != "INGRESS" or rule.disabled or not rule.allowed: #nothing to do here returning with empty list
        return findings
    if OPEN_TO_WORLD not in rule.source_ranges:
        return findings

    for allowed in rule.allowed:
        protocol = allowed.I_p_protocol.lower()

        if protocol == "icmp":
            continue

        if protocol == "all":
            findings.append({
                "severity": "CRITICAL",
                "description": "ALL protocols and ports open to the entire internet",
            })
            continue

        if protocol in ("tcp", "udp"):
            ports = list(allowed.ports) if allowed.ports else None

            if ports is None:
                findings.append({
                    "severity": "HIGH",
                    "description": f"ALL {protocol.upper()} ports open to the entire internet",
                })
            else:
                for port in ports:
                    if port in RISKY_PORTS:
                        findings.append({
                            "severity": "HIGH",
                            "description": f"{protocol.upper()} port {port}"
                            f" ({RISKY_PORTS[port]}) open to the entire internet",
                        })

    return findings

def scan_firewalls(project_id):
    client = compute_v1.FirewallsClient()
    rules = list(client.list(project=project_id))
    findings = []

    for rule in rules:
        for f in evaluate_rule(rule):
            findings.append({
                "scanner": "Firewall",
                "severity": f["severity"],
                "resource": rule.name,
                "description": f["description"],
                "fix": "Restrict the source range to specific trusted IPs instead of "
                       "0.0.0.0/0, or remove the rule if it's unused.",
            })

    return findings

if __name__ == "__main__":
    print(f"Scanning firewall rules for project '{PROJECT_ID}'...")
    results = scan_firewalls(PROJECT_ID)
    if not results:
        print("○ No risky firewall rules found.")
    else:
        print(f"● Found {len(results)} finding(s):")
        for f in results:
            print(f"  -> [{f['severity']}] {f['resource']}: {f['description']}")
            print(f"     FIX: {f['fix']}")
    print("Scan complete.")
