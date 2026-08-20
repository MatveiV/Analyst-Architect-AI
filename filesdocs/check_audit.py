import sys
sys.path.insert(0, r"C:\GitHub\3A\filesdocs")
import test_demo_flow as t

token = t.get_token()
st = t.load_state()

status, body = t.api("GET", "/audit", token=token, timeout=30)
print("audit list:", status, "runs:", len(body) if status == 200 else body)
if status == 200:
    for r in body[:8]:
        print(f"  {r['action']} {r['created_at'][11:19]} dur={r['duration_ms']}ms "
              f"provider={r.get('provider_used')} local={r.get('is_local_provider')} "
              f"status={r['status']}")
    st["audit"] = {"runs": len(body)}
    t.save_state(st)

status, body = t.api("GET", "/audit/stats", token=token, timeout=30)
print("audit stats:", status, str(body)[:400])