import os, requests
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
    except: return {"error": "failed"}

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
        name = i.get("jobName", "Unknown")
        prefix = name.split(" - ",1)[0] if " - " in name else name[:15]
        size = round((i.get("sourceSize") or 0) / (1024**3), 2)
        r.append({"prefix": prefix, "size": size})
    return r

@app.route("/")
def index():
    comp = get_companies()
    vm_sum = defaultdict(float)
    for v in get_vms():
        org = v.get("organizationUid","")
        name = comp.get(org, "Unknown")
        vm_sum[name] += round((v.get("usedSourceSize") or 0) / (1024**3), 2)
    vm_list = sorted([{"c":k,"t":round(v,2)} for k,v in vm_sum.items() if v>0], key=lambda x:x["c"].lower())

    ws_sum = defaultdict(float)
    for w in get_workstations():
        ws_sum[w["prefix"]] += w["size"]
    ws_list = sorted([{"c":k,"t":round(v,2)} for k,v in ws_sum.items() if v>0], key=lambda x:x["c"].lower())

    return f"""
    <h1 style="color:#006400">Veeam Backup Sizes - Adept Networks</h1>
    <button onclick="location.reload()" style="padding:15px 30px;background:#006400;color:white;border:none;font-size:18px;cursor:pointer">Pull Fresh Data</button>
    <h2>Virtual Machines - Summary by Company</h2>
    <table border="1" style="width:100%"><tr style="background:#006400;color:white"><th>Company</th><th>Total GB</th></tr>
    {''.join(f"<tr><td>{x['c']}</td><td>{x['t']}</td></tr>" for x in vm_list)}</table>
    <h2>Workstations - Summary by Job Prefix</h2>
    <table border="1" style="width:100%"><tr style="background:#006400;color:white"><th>Tenant / Prefix</th><th>Total GB</th></tr>
    {''.join(f"<tr><td>{x['c']}</td><td>{x['t']}</td></tr>" for x in ws_list)}</table>
    <p><strong>VMs:</strong> {len(get_vms())} | <strong>Workstation Jobs:</strong> {len(get_workstations())}</p>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
