import os
import requests
from flask import Flask, render_template_string
from collections import defaultdict

app = Flask(__name__)

VSPC_URL = "https://veeam.adeptnetworks.com:1280/api"
TOKEN = os.environ.get("API_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

def api(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}"}
        return r.json()
    except:
        return {"error": "request failed"}

def get_companies():
    data = api(f"{VSPC_URL}/v3/organizations/companies")
    if "error" in data: return {}
    return {c["instanceUid"]: c["name"] for c in data.get("data", []) if "instanceUid" in c}

def get_vms():
    url = f"{VSPC_URL}/v3/protectedWorkloads/virtualMachines"
    vms, offset = [], 0
    while True:
        data = api(f"{url}?offset={offset}&take=100")
        if "error" in data or not data.get("data"): break
        vms.extend(data["data"])
        total = data.get("meta", {}).get("pagingInfo", {}).get("total", 0)
        if offset + 100 >= total: break
        offset += 100
    return vms

def get_workstations():
    data = api(f"{VSPC_URL}/v3/protectedWorkloads/computersManagedByConsole/jobs")
    if "error" in data or not data.get("data"): return []
    result = []
    for item in data["data"]:
        job_name = item.get("jobName", "Unknown")
        size_gb = round((item.get("sourceSize") or 0) / (1024**3), 2)
        # Extract prefix (first part before " - " or first 10 chars)
        prefix = job_name.split(" - ", 1)[0] if " - " in job_name else job_name[:10]
        result.append({"prefix": prefix, "size_gb": size_gb})
    return result

def get_data():
    companies = get_companies()

    # VMs
    vm_summary = defaultdict(float)
    for vm in get_vms():
        size_gb = round((vm.get("usedSourceSize") or 0) / (1024**3), 2)
        org_uid = vm.get("organizationUid", "")
        company_name = companies.get(org_uid, "Unknown")
        vm_summary[company_name] += size_gb
    vm_summary_list = [{"company": k, "total": round(v, 2)} for k, v in vm_summary.items() if v > 0]
    vm_summary_list.sort(key=lambda x: x["company"].lower())

    # WORKSTATIONS — using job name prefix (the only reliable method on your server)
    ws_by_prefix = defaultdict(float)
    for ws in get_workstations():
        ws_by_prefix[ws["prefix"]] += ws["size_gb"]

    workstations = [
        {"company": prefix, "total": round(total, 2)}
        for prefix, total in ws_by_prefix.items() if total > 0
    ]
    workstations.sort(key=lambda x: x["company"].lower())

    if not workstations:
        workstations = [{"company": "No workstation data", "total": 0}]

    return {
        "vm_summary": vm_summary_list,
        "workstations": workstations,
        "vm_count": len(get_vms()),
        "ws_job_count": len(get_workstations())
    }

@app.route("/")
def index():
    data = get_data()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Veeam Dashboard - Adept Networks</title>
        <style>
            body {{font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5;}}
            h1, h2 {{color: #006400;}}
            table {{width: 100%; border-collapse: collapse; margin: 25px 0;}}
            th, td {{border: 1px solid #ccc; padding: 12px; text-align: left;}}
            th {{background: #006400; color: white;}}
            button {{padding: 15px 30px; background: #006400; color: white; border: none; font-size: 18px; cursor: pointer;}}
        </style>
    </head>
    <body>
        <h1>Veeam Backup Sizes - Adept Networks</h1>
        <button onclick="location.reload()">Pull Fresh Data</button>

        <h2>Virtual Machines - Summary by Company</h2>
        <table>
            <tr><th>Company</th><th>Total Source Size (GB)</th></tr>
            {''.join(f"<tr><td>{c['company']}</td><td>{c['total']}</td></tr>" for c in data['vm_summary'])}
        </table>

        <h2>Workstations - Summary by Job Name Prefix</h2>
        <table>
            <tr><th>Tenant / Job Prefix</th><th>Total Source Size (GB)</th></tr>
            {''.join(f"<tr><td>{c['company']}</td><td>{c['total']}</td></tr>" for c in data['workstations'])}
        </table>

        <h2>Stats → VMs: {data['vm_count']} | Workstation Jobs Found: {data['ws_job_count']}</h2>
    </body>
    </html>
    """
    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)