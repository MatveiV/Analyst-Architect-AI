"""Run one ArchStudio step at a time: urs|srs|adr|diagrams|coverage|exports."""
import sys

sys.path.insert(0, r"C:\GitHub\3A\filesdocs")
import test_demo_flow as t

token = t.get_token()
st = t.load_state()
which = sys.argv[1]
full_id = st["docs"]["crm"]["full_id"]
arch = st.setdefault("arch", {})

if which == "standards":
    status, body = t.api("PATCH", f"/documents/{full_id}/standards", body={
        "default_requirements_standard": "GOST_34_602",
        "default_diagram_standard": "UML",
    }, token=token, timeout=30)
    print(f"standards set -> status={status} body={body}")

elif which == "urs":
    if "urs" not in arch:
        print("[ARCH] URS (LLM) ...", flush=True)
        status, body = t.api("POST", f"/documents/{full_id}/generate-urs", body={}, token=token, timeout=900)
        if status == 200:
            arch["urs"] = {"needs_review": body.get("needs_review"),
                           "confidence": body.get("confidence"),
                           "ureq": len(body.get("user_requirements", []) or [])}
            print(f"URS -> needs_review={body.get('needs_review')} conf={body.get('confidence')} "
                  f"ureq={len(body.get('user_requirements', []) or [])}", flush=True)
        else:
            print(f"URS FAILED status={status} body={str(body)[:300]}", flush=True)
        t.save_state(st)

elif which == "srs":
    if "srs" not in arch:
        print("[ARCH] SRS (LLM) ...", flush=True)
        status, body = t.api("POST", f"/documents/{full_id}/generate-srs", body={}, token=token, timeout=900)
        if status == 200:
            arch["srs"] = {"needs_review": body.get("needs_review"),
                           "confidence": body.get("confidence"),
                           "freq": len(body.get("functional_requirements", []) or [])}
            print(f"SRS -> needs_review={body.get('needs_review')} conf={body.get('confidence')} "
                  f"freq={len(body.get('functional_requirements', []) or [])}", flush=True)
        else:
            print(f"SRS FAILED status={status} body={str(body)[:300]}", flush=True)
        t.save_state(st)

elif which == "adr":
    if "adr" not in arch:
        print("[ARCH] ADR (LLM) ...", flush=True)
        status, body = t.api("POST", f"/documents/{full_id}/generate-adr", body={}, token=token, timeout=900)
        if status == 200:
            title = (body.get("adr_json") or "{}")
            import json
            try:
                title = json.loads(title).get("title", "?")
            except Exception:
                pass
            arch["adr"] = {"title": str(title)[:60]}
            print(f"ADR -> {arch['adr']['title']}", flush=True)
        else:
            print(f"ADR FAILED status={status} body={str(body)[:300]}", flush=True)
        t.save_state(st)

elif which == "diagrams":
    if "diagrams" not in arch:
        print("[ARCH] Diagrams (LLM) ...", flush=True)
        status, body = t.api("POST", f"/documents/{full_id}/generate-diagrams", body={}, token=token, timeout=900)
        if status == 200:
            created = body.get("created", [])
            ok = sum(1 for c in created if c["render_status"] == "ok")
            arch["diagrams"] = {"count": len(created), "rendered_ok": ok,
                                "standard": body.get("standard_profile")}
            print(f"Diagrams -> created={len(created)} rendered_ok={ok} "
                  f"standard={body.get('standard_profile')}", flush=True)
            for c in created:
                print(f"   {c['type']}: {c['render_status']}", flush=True)
        else:
            print(f"Diagrams FAILED status={status} body={str(body)[:300]}", flush=True)
        t.save_state(st)

elif which == "coverage":
    status, body = t.api("GET", f"/documents/{full_id}/coverage", token=token, timeout=30)
    if status == 200:
        arch["coverage"] = {
            "has_requirements": body.get("has_requirements"),
            "has_diagrams": body.get("has_diagrams"),
            "has_acceptance_criteria": body.get("has_acceptance_criteria"),
            "is_fully_covered": body.get("is_fully_covered"),
            "req_source": body.get("requirements_source"),
            "diagrams_count": body.get("diagrams_count"),
        }
        print(f"Coverage -> full={body.get('is_fully_covered')} req={body.get('has_requirements')} "
              f"diag={body.get('has_diagrams')} crit={body.get('has_acceptance_criteria')} "
              f"source={body.get('requirements_source')} diagrams={body.get('diagrams_count')}", flush=True)
    else:
        print(f"Coverage FAILED status={status} body={str(body)[:200]}", flush=True)
    t.save_state(st)

elif which == "exports":
    for ep in ["export/markdown", "export/docx", "export/full-package/docx"]:
        status, _ = t.api("GET", f"/documents/{full_id}/{ep}", token=token, timeout=90, raw=True)
        print(f"export {ep} -> status={status}", flush=True)

else:
    print("usage: arch_step.py standards|urs|srs|adr|diagrams|coverage|exports")