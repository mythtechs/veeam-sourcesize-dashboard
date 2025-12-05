

import os
import requests
from flask import Flask
from collections import defaultdict

app = Flask(__name__)
VSPC_URL = "https://veeam.adeptnetworks.com:1280/api"
TOKEN = os.environ.get("API_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}

def api(u):
    try:
        r = requests.get(u, headers=HEADERS, timeout=30)
        return r.json() if r.status_code == 200 else {"error": r.status_code}
    except:
        return {"error": "failed"}

def get_companies():
    d = api(f"{VSPC_URL}/v3/organizations/companies")
    if "error" in d: return {}
    return {c["instanceUid"]: c["name"] for c in d.get("data",[]) if "instanceUid" in c}

def get_vms():
    vms, o = [], 0
    while True:
        d = api(f"{VSPC_URL}/v3/protectedWorkloads/virtualMachines?offset={o}&take=100")
        if "error" in d or not d.get("data"): break
        vms.extend(d["data"])
        if o + 100 >= d.get("meta",{}).get("pagingInfo",{}).get("total",0): break
        o += 100
    return vms

def get_workstations():
    d = api(f"{VSPC_URL}/v3/protectedWorkloads/computersManagedByConsole/jobs")
    if "error" in d or not d.get("data"): return []
    r = []
    for i in d["data"]:
        org_uid = i.get("organizationUid")
        name = i.get("jobName", "Unknown")
        size = round((i.get("sourceSize") or 0) / (1024**3), 2)
        # Use organizationUid if available, else fallback to job name prefix
        group_key = org_uid if org_uid else (name.split(" - ",1)[0] if " - " in name else name[:15])
        r.append({"group": group_key, "size": size})
    return r

@app.route("/")
def index():
    comp = get_companies()
    
    # VMs
    vm_sum = defaultdict(float)
    for v in get_vms():
        org = v.get("organizationUid","")
        name = comp.get(org, "Unknown")
        vm_sum[name] += round((v.get("usedSourceSize") or 0) / (1024**3), 2)
    vm_list = sorted([{"c":k,"t":round(v,2)} for k,v in vm_sum.items() if v>0], key=lambda x:x["c"].lower())

    # Workstations — grouped by organizationUid (fallback to prefix)
    ws_sum = defaultdict(float)
    for w in get_workstations():
        ws_sum[w["group"]] += w["size"]
    ws_list = []
    for group, total in ws_sum.items():
        if group in comp:  # If it's an organizationUid, use company name
            ws_list.append({"c": comp[group], "t": round(total, 2)})
        else:  # Else, use the prefix as-is
            ws_list.append({"c": group, "t": round(total, 2)})
    ws_list = sorted(ws_list, key=lambda x: x["c"].lower())

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Veeam Dashboard - Adept Networks</title>
        <meta charset="utf-8">
        <style>
            body {{font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5;}}
            h1 {{color: #006400; text-align: center;}}
            button {{padding: 15px 30px; background: #006400; color: white; border: none; font-size: 18px; cursor: pointer; display: block; margin: 20px auto;}}
            .container {{display: flex; gap: 30px; flex-wrap: wrap; justify-content: center;}}
            .panel {{flex: 1; min-width: 450px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);}}
            h2 {{color: #006400; margin-top: 0;}}
            table {{width: 100%; border-collapse: collapse; margin-top: 10px;}}
            th, td {{border: 1px solid #ccc; padding: 10px; text-align: left;}}
            th {{background: #006400; color: white;}}
            .stats {{text-align: center; margin: 30px 0; font-size: 18px; color: #333;}}
        </style>
    </head>
    <body>
        <h1>Veeam Backup Sizes - Adept Networks</h1>
        <button onclick="location.reload()">Pull Fresh Data</button>

        <div class="container">
            <div class="panel">
                <h2>Virtual Machines - Summary by Company</h2>
                <table>
                    <tr><th>Company</th><th>Total GB</th></tr>
                    {''.join(f"<tr><td>{x['c']}</td><td>{x['t']}</td></tr>" for x in vm_list)}
                </table>
            </div>

            <div class="panel">
                <h2>Workstations - Summary by Tenant/Prefix</h2>
                <table>
                    <tr><th>Tenant / Prefix</th><th>Total GB</th></tr>
                    {''.join(f"<tr><td>{x['c']}</td><td>{x['t']}</td></tr>" for x in ws_list)}
                </table>
            </div>
        </div>

        <div class="stats">
            <strong>VMs:</strong> {len(get_vms())} | <strong>Workstation Jobs Found:</strong> {len(get_workstations())}
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
