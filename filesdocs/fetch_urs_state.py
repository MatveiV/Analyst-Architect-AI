"""Fetch URS/SRS state from server after client-side timeouts."""
import sys

sys.path.insert(0, r"C:\GitHub\3A\filesdocs")
import test_demo_flow as t

token = t.get_token()
st = t.load_state()
full_id = st["docs"]["crm"]["full_id"]
arch = st.setdefault("arch", {})

# 1. audit log
status, body = t.api("GET", "/audit?limit=10", token=token, timeout=30)
print("audit:", status)
if status == 200:
    for r in body:
        print(f"  {r['action']} {r['created_at'][11:19]} dur={r['duration_ms']}ms "
              f"in={r.get('input_tokens')} out={r.get('output_tokens')} status={r['status']}")

# 2. requirements documents history
status, body = t.api("GET", f"/documents/{full_id}/requirements-documents", token=token, timeout=30)
print("req-docs:", status)
if status == 200:
    for rd in body:
        cj = (rd.get("content_json") or "{}")
        import json
        try:
            c = json.loads(cj)
            n = len(c.get("user_requirements") or c.get("functional_requirements") or [])
        except Exception:
            n = 0
        print(f"  {rd['doc_kind']} standard={rd['standard_profile']} "
              f"needs_review={rd['needs_review']} conf={rd['confidence']} items={n}")
        if rd["doc_kind"] == "urs" and "urs" not in arch:
            arch["urs"] = {"needs_review": rd["needs_review"], "confidence": rd["confidence"], "ureq": n}
        if rd["doc_kind"] == "srs" and "srs" not in arch:
            arch["srs"] = {"needs_review": rd["needs_review"], "confidence": rd["confidence"], "freq": n}

# 3. ADR
status, body = t.api("GET", "/documents", token=token, timeout=30)
if status == 200:
    pass

t.save_state(st)
print("state saved")