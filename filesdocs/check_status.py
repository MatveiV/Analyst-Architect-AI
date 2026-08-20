import sys
sys.path.insert(0, r"C:\GitHub\3A\filesdocs")
import test_demo_flow as t

token = t.get_token()
st = t.load_state()

if "audit" in sys.argv:
    status, body = t.api("GET", "/audit/runs?limit=15", token=token, timeout=30)
    print("audit status:", status)
    if status == 200:
        for r in body:
            print(f"  {r['action']} {r['created_at'][11:19]} dur={r['duration_ms']}ms in={r.get('input_tokens')} out={r.get('output_tokens')} err={r.get('error')}")

if "batch" in sys.argv:
    status, body = t.api("GET", "/batch-reviews", token=token, timeout=30)
    print("batch list status:", status)
    if status == 200 and body:
        for b in body:
            print(f"  batch {b['id'][:8]} status={b['status']} total={b['total_count']} "
                  f"completed={b['completed_count']} nr={b['needs_review_count']} err={b['error_count']}")
        bid = body[0]["id"]
        status, detail = t.api("GET", f"/batch-reviews/{bid}", token=token, timeout=30)
        if status == 200:
            for it in detail["items"]:
                print(f"    {it['order_index']}: {it['title'][:30]} status={it['status']} "
                      f"nr={it['needs_review']} conf={it['confidence']}")
    else:
        print("  no batches")

if "docs" in sys.argv:
    status, body = t.api("GET", "/documents", token=token, timeout=30)
    print("docs status:", status, "count:", len(body) if status == 200 else body)

if "dash" in sys.argv:
    for path in ["/dashboard/stats-by-provider", "/dashboard/stats", "/dashboard/actual-usage"]:
        status, body = t.api("GET", path, token=token, timeout=30)
        print(f"{path} -> status={status} body={str(body)[:200]}")