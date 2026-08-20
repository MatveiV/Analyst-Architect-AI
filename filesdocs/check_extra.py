"""Test review diff, CSV exports, reviews list."""
import sys
sys.path.insert(0, r"C:\GitHub\3A\filesdocs")
import test_demo_flow as t

token = t.get_token()
st = t.load_state()

# reviews list
status, body = t.api("GET", "/reviews", token=token, timeout=30)
print("reviews list:", status, "count:", len(body) if status == 200 else body)
if status == 200 and body:
    ids = [r["id"] for r in body]
    print("  review ids:", [i[:8] for i in ids[:6]])

# review diff between two runs of the same doc (crm_full has 2 reviews: manual + batch)
status, body = t.api("GET", "/reviews?document_id=efd4c750-7628-4224-a0ba-37d309515f2c",
                     token=token, timeout=30)
print("crm_full reviews:", status, str(body)[:200] if status != 200 else f"{len(body)} runs")

# diff endpoint
if status == 200 and len(body) >= 2:
    rid1, rid2 = body[0]["id"], body[1]["id"]
    status, diff = t.api("GET", f"/reviews/reviews/diff?from_review_id={rid1}&to_review_id={rid2}",
                         token=token, timeout=30)
    print("diff:", status, str(diff)[:300])

# CSV exports
for label, path in [
    ("batch csv", f"/batch-reviews/{st['batch']['id']}/export/csv"),
    ("lessons csv", "/lessons/export/csv"),
    ("review json", f"/reviews/{ids[0]}/export/json" if body else None),
]:
    if not path:
        continue
    status, raw = t.api("GET", path, token=token, timeout=30, raw=True)
    print(label, "->", status, f"{len(raw)} bytes" if status == 200 else str(raw)[:200])

# risk catalog (auto-populated from reviews)
status, body = t.api("GET", "/risk-catalog", token=token, timeout=30)
print("risk catalog:", status, "count:", len(body) if status == 200 else body)
if status == 200:
    for r in body[:5]:
        print(f"  {r.get('title','')[:60]} severity={r.get('severity')}")

# lessons list
status, body = t.api("GET", "/lessons", token=token, timeout=30)
print("lessons:", status, "count:", len(body) if status == 200 else body)
if status == 200:
    for l in body[:5]:
        print(f"  {l['title'][:60]} impact={l['impact_type']} source={l['source']}")

# KB docs (auto-indexed URS/SRS/ADR)
status, body = t.api("GET", "/kb/documents", token=token, timeout=30)
print("kb documents:", status, "count:", len(body) if status == 200 else body)
if status == 200:
    auto = [d for d in body if d.get("source_type")]
    print("  auto-indexed:", len(auto))
    for d in auto[:8]:
        print(f"  [{d.get('source_type')}] {d['title'][:60]}")

# standards list
status, body = t.api("GET", "/standards", token=token, timeout=30)
print("standards:", status, "count:", len(body) if status == 200 else body)