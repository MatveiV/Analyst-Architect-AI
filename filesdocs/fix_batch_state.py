import json
import sys

sys.path.insert(0, r"C:\GitHub\3A\filesdocs")
import test_demo_flow as t

st = t.load_state()
token = t.get_token()

# Save the completed batch (client timed out but server finished)
status, body = t.api("GET", "/batch-reviews", token=token, timeout=30)
if status == 200 and body:
    b = body[0]
    st["batch"] = {
        "id": b["id"],
        "status": b["status"],
        "total": b["total_count"],
        "completed": b["completed_count"],
        "needs_review": b["needs_review_count"],
        "errors": b["error_count"],
    }
    t.save_state(st)
    print("batch saved:", st["batch"])
else:
    print("batch fetch failed:", status, str(body)[:200])