"""End-to-end functional test for Analyst-Architect-AI using demo documents."""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
USER = os.environ.get("API_USER", "admin")
PASS = os.environ.get("API_PASS", "admin123")
TOKEN_FILE = os.path.join(os.environ.get("TEMP", "."), "3a_test_token.txt")

DOCS = {
    "crm": {
        "name": "CRM для заказов на разработку",
        "full": r"C:\GitHub\3A\filesdocs\demo-documents\01-crm-razrabotka\01_TZ_polnoe.md",
        "raw": r"C:\GitHub\3A\filesdocs\demo-documents\01-crm-razrabotka\02_TZ_syroe_dlya_review.md",
        "kb": [
            r"C:\GitHub\3A\filesdocs\demo-documents\01-crm-razrabotka\03_KB_pravila_komandy.md",
            r"C:\GitHub\3A\filesdocs\demo-documents\01-crm-razrabotka\04_KB_chastye_voprosy.md",
            r"C:\GitHub\3A\filesdocs\demo-documents\01-crm-razrabotka\05_KB_slovar_terminov.md",
        ],
        "lessons": r"C:\GitHub\3A\filesdocs\demo-documents\01-crm-razrabotka\06_Urok_proekta.md",
    },
    "trading": {
        "name": "Торговая платформа",
        "full": r"C:\GitHub\3A\filesdocs\demo-documents\02-trading-platform\01_TZ_polnoe.md",
        "raw": r"C:\GitHub\3A\filesdocs\demo-documents\02-trading-platform\02_TZ_syroe_dlya_review.md",
        "kb": [
            r"C:\GitHub\3A\filesdocs\demo-documents\02-trading-platform\03_KB_pravila_komandy.md",
            r"C:\GitHub\3A\filesdocs\demo-documents\02-trading-platform\04_KB_chastye_voprosy.md",
            r"C:\GitHub\3A\filesdocs\demo-documents\02-trading-platform\05_KB_slovar_terminov.md",
        ],
        "lessons": r"C:\GitHub\3A\filesdocs\demo-documents\02-trading-platform\06_Urok_proekta.md",
    },
    "insurance": {
        "name": "Система управления страховыми продуктами",
        "full": r"C:\GitHub\3A\filesdocs\demo-documents\03-insurance\01_TZ_polnoe.md",
        "raw": r"C:\GitHub\3A\filesdocs\demo-documents\03-insurance\02_TZ_syroe_dlya_review.md",
        "kb": [
            r"C:\GitHub\3A\filesdocs\demo-documents\03-insurance\03_KB_pravila_komandy.md",
            r"C:\GitHub\3A\filesdocs\demo-documents\03-insurance\04_KB_chastye_voprosy.md",
            r"C:\GitHub\3A\filesdocs\demo-documents\03-insurance\05_KB_slovar_terminov.md",
        ],
        "lessons": r"C:\GitHub\3A\filesdocs\demo-documents\03-insurance\06_Urok_proekta.md",
    },
}

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_state.json")


def api(method, path, body=None, token=None, timeout=30, raw=False, params=None):
    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            if raw:
                return resp.status, content
            return resp.status, json.loads(content.decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
        except Exception:
            detail = str(e)
        return e.code, detail
    except Exception as e:
        return -1, str(e)


def login():
    # OAuth2 password flow: form-encoded, not JSON
    form = urllib.parse.urlencode({"username": USER, "password": PASS}).encode("utf-8")
    req = urllib.request.Request(BASE + "/auth/login", data=form,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            status = 200
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = str(e)
    if status != 200:
        print(f"[AUTH] FAILED status={status} body={body}")
        sys.exit(1)
    token = body["access_token"]
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    print(f"[AUTH] OK token={token[:25]}...")
    return token


def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return login()


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def read_file(path):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1251")


def phase_auth():
    token = login()
    # also verify health
    status, body = api("GET", "/health", timeout=10)
    print(f"[HEALTH] status={status} body={body}")
    return token


def phase_upload(token, state):
    """Upload all TZ + KB documents."""
    docs = state.setdefault("docs", {})
    kb = state.setdefault("kb_docs", {})
    for key, cfg in DOCS.items():
        # full TZ
        fname = cfg["full"]
        text = read_file(fname)
        status, body = api("POST", "/documents", body={
            "title": cfg["name"],
            "text": text,
            "doc_type": "tz",
            "project_name": key,
        }, token=token, timeout=30)
        if status == 200:
            docs[key] = {"full_id": body["id"]}
            print(f"[DOC] {key} full -> {body['id'][:8]}")
        else:
            print(f"[DOC] {key} full FAILED status={status} body={str(body)[:200]}")

        # raw TZ
        text = read_file(cfg["raw"])
        status, body = api("POST", "/documents", body={
            "title": cfg["name"] + " (сырое ТЗ)",
            "text": text,
            "doc_type": "tz",
            "project_name": key,
        }, token=token, timeout=30)
        if status == 200:
            docs[key]["raw_id"] = body["id"]
            print(f"[DOC] {key} raw -> {body['id'][:8]}")
        else:
            print(f"[DOC] {key} raw FAILED status={status} body={str(body)[:200]}")

        # KB docs
        kb[key] = []
        for i, kbfile in enumerate(cfg["kb"]):
            text = read_file(kbfile)
            status, body = api("POST", "/kb/documents", body={
                "title": f"KB {key} #{i+1}",
                "text": text,
                "doc_type": "kb_article",
                "project_name": key,
            }, token=token, timeout=30)
            if status == 200:
                kb[key].append(body["id"])
                print(f"[KB] {key} #{i+1} -> {body['id'][:8]}")
            else:
                print(f"[KB] {key} #{i+1} FAILED status={status}")
    save_state(state)
    return state


def phase_reviews(token, state):
    """Run AI review on all uploaded TZ docs."""
    docs = state.get("docs", {})
    reviews = state.setdefault("reviews", {})
    for key, cfg in DOCS.items():
        for kind in ("full", "raw"):
            if key not in docs or kind not in docs[key]:
                continue
            doc_id = docs[key][kind]
            rkey = f"{key}_{kind}"
            if rkey in reviews:
                print(f"[REVIEW] {rkey} already done")
                continue
            print(f"[REVIEW] {rkey} starting (doc={doc_id[:8]}) ...")
            status, body = api("POST", f"/documents/{doc_id}/review", body={},
                               token=token, timeout=600)
            if status == 200:
                reviews[rkey] = {
                    "id": body["id"], "needs_review": body["needs_review"],
                    "confidence": body["confidence"],
                }
                rj = json.loads(body["review_json"])
                print(f"[REVIEW] {rkey} -> needs_review={body['needs_review']} "
                      f"confidence={body['confidence']} risks={len(rj.get('risks', []))} "
                      f"missing={len(rj.get('missing_requirements', []))} "
                      f"criteria={len(rj.get('acceptance_criteria', []))}")
            else:
                print(f"[REVIEW] {rkey} FAILED status={status} body={str(body)[:300]}")
            save_state(state)
    return state


def phase_batch(token, state):
    """Create a batch review with all 6 TZ docs."""
    items = []
    for key, cfg in DOCS.items():
        for kind in ("full", "raw"):
            fpath = cfg["full"] if kind == "full" else cfg["raw"]
            items.append({
                "title": f"{key}_{kind}",
                "text": read_file(fpath),
            })
    status, body = api("POST", "/batch-reviews", body={
        "title": "Demo batch: all 3 topics",
        "items": items,
        "reasoning_mode": "direct",
    }, token=token, timeout=900)
    if status == 200:
        state["batch"] = {
            "id": body["id"],
            "status": body["status"],
            "total": body["total_count"],
            "completed": body["completed_count"],
            "needs_review": body["needs_review_count"],
            "errors": body["error_count"],
        }
        print(f"[BATCH] id={body['id'][:8]} status={body['status']} "
              f"total={body['total_count']} completed={body['completed_count']} "
              f"needs_review={body['needs_review_count']} errors={body['error_count']}")
        for it in body["items"]:
            print(f"  - {it['title']}: {it['status']} needs_review={it['needs_review']} "
                  f"conf={it['confidence']}")
        save_state(state)
    else:
        print(f"[BATCH] FAILED status={status} body={str(body)[:400]}")
    return state


def phase_kb_ask(token, state):
    """Ask a question against the knowledge base."""
    questions = [
        "Что делать, если аналитик оценил проект, а клиент изменил требования?",
        "Как формируется себестоимость проекта по часам разработчиков?",
    ]
    qa = state.setdefault("kb_answers", [])
    for q in questions:
        print(f"[KB] asking: {q[:60]}...")
        status, body = api("POST", "/kb/ask", body={"question": q}, token=token, timeout=300)
        if status == 200:
            qa.append({
                "question": q,
                "answer": body.get("answer", "")[:200],
                "sources": len(body.get("sources", [])),
                "confidence": body.get("confidence"),
                "needs_review": body.get("needs_review"),
            })
            print(f"[KB] -> sources={len(body.get('sources', []))} "
                  f"confidence={body.get('confidence')} needs_review={body.get('needs_review')}")
            for s in body.get("sources", [])[:3]:
                print(f"      src: {s.get('document_title', '?')[:60]}")
        else:
            print(f"[KB] FAILED status={status} body={str(body)[:300]}")
    save_state(state)
    return state


def phase_lessons(token, state):
    """Create lessons from the lesson demo files."""
    lessons = state.setdefault("lessons", [])
    # Lesson 1 (negative, estimation) - from CRM topic
    lessons_data = [
        {
            "project_name": "crm",
            "title": "Недооценили интеграцию с Jira для учёта часов",
            "description": "На этапе оценки закладывали 16 часов на интеграцию с Jira Cloud API для автоматической выгрузки отработанных часов. По факту ушло 48 часов — Jira Cloud API оказался с нестандартной пагинацией и требовал отдельной обработки rate limit (429 ошибки при массовой синхронизации). Обнаружили проблему только на этапе интеграционного тестирования.",
            "category": "estimation",
            "impact_type": "negative",
            "root_cause": "Аналитик оценивал интеграцию по документации без пилотного вызова API — реальные ограничения (rate limit, формат пагинации) выяснились только в момент написания кода.",
            "recommendation": "Для любой внешней интеграции с незнакомым API закладывать в оценку минимум 4 часа на пилотный «hello world» вызов реального API ДО финальной оценки трудоёмкости.",
        },
        {
            "project_name": "crm",
            "title": "Чек-лист передачи лида в проект снял путаницу с командой",
            "description": "После внедрения обязательного чек-листа передачи случаи, когда проект стартовал без назначенного backend-разработчика, сократились с 3 за квартал до нуля.",
            "category": "process",
            "impact_type": "positive",
            "root_cause": "",
            "recommendation": "Использовать этот же паттерн (обязательный чек-лист на границе между отделами) для передачи проекта от PM к отделу поддержки после релиза.",
        },
    ]
    for ld in lessons_data:
        status, body = api("POST", "/lessons", body=ld, token=token, timeout=30)
        if status == 200:
            lessons.append({"id": body["id"], "title": body["title"], "source": body["source"]})
            print(f"[LESSON] {body['title'][:50]} -> {body['id'][:8]} source={body['source']}")
        else:
            print(f"[LESSON] FAILED status={status} body={str(body)[:200]}")
    save_state(state)
    return state


def phase_economics(token, state):
    """Create build project, estimate tasks, economic estimate."""
    docs = state.get("docs", {})
    full_id = docs.get("crm", {}).get("full_id")
    if not full_id:
        print("[ECON] no full doc, skip")
        return state
    # create build project
    status, body = api("POST", "/build-projects", body={
        "document_id": full_id,
        "name": "CRM для заказов на разработку",
        "description": "Тестовый build-project на основе полного ТЗ CRM",
    }, token=token, timeout=30)
    if status != 200:
        print(f"[ECON] create project FAILED status={status} body={str(body)[:200]}")
        return state
    pid = body["id"]
    state["econ"] = {"project_id": pid}
    print(f"[ECON] project created -> {pid[:8]} status={body['status']}")
    save_state(state)

    # estimate tasks (LLM)
    print("[ECON] estimating tasks (LLM) ...")
    status, body = api("POST", f"/build-projects/{pid}/estimate-tasks", body={},
                       token=token, timeout=600)
    if status == 200:
        state["econ"]["task_estimate_id"] = body["id"]
        state["econ"]["total_hours"] = body["total_hours"]
        state["econ"]["confidence"] = body["confidence"]
        print(f"[ECON] task estimate -> id={body['id'][:8]} hours={body['total_hours']} "
              f"conf={body['confidence']}")
    else:
        print(f"[ECON] estimate-tasks FAILED status={status} body={str(body)[:300]}")
    save_state(state)

    # economic estimate
    status, body = api("POST", f"/build-projects/{pid}/economic-estimate?use_actual_llm_cost=true",
                       body={}, token=token, timeout=30)
    if status == 200:
        state["econ"]["economic_id"] = body["id"]
        state["econ"]["capex"] = body["capex"]
        state["econ"]["opex_monthly"] = body["opex_monthly"]
        state["econ"]["roi_12m_pct"] = body["roi_12m_pct"]
        state["econ"]["llm_cost_source"] = body["llm_cost_source"]
        print(f"[ECON] economic -> capex={body['capex']:.0f} opex={body['opex_monthly']:.0f} "
              f"roi12m={body['roi_12m_pct']:.1f}% source={body['llm_cost_source']}")
    else:
        print(f"[ECON] economic-estimate FAILED status={status} body={str(body)[:300]}")
    save_state(state)
    return state


def phase_archstudio(token, state):
    """Generate URS/SRS/ADR/diagrams + coverage + exports for the full CRM TZ."""
    docs = state.get("docs", {})
    full_id = docs.get("crm", {}).get("full_id")
    if not full_id:
        print("[ARCH] no full doc, skip")
        return state

    # set standards: GOST 34 for requirements, UML for diagrams
    status, body = api("PATCH", f"/documents/{full_id}/standards", body={
        "default_requirements_standard": "GOST_34_602",
        "default_diagram_standard": "UML",
    }, token=token, timeout=30)
    print(f"[ARCH] set standards -> status={status}")

    arch = state.setdefault("arch", {})

    # URS
    print("[ARCH] generating URS (LLM) ...")
    status, body = api("POST", f"/documents/{full_id}/generate-urs", body={},
                       token=token, timeout=600)
    if status == 200:
        arch["urs"] = {
            "needs_review": body.get("needs_review"),
            "confidence": body.get("confidence"),
            "user_req": len(body.get("user_requirements", []) or []),
        }
        print(f"[ARCH] URS -> needs_review={body.get('needs_review')} "
              f"conf={body.get('confidence')} ureq={len(body.get('user_requirements', []) or [])}")
    else:
        print(f"[ARCH] URS FAILED status={status} body={str(body)[:300]}")
    save_state(state)

    # SRS
    print("[ARCH] generating SRS (LLM) ...")
    status, body = api("POST", f"/documents/{full_id}/generate-srs", body={},
                       token=token, timeout=600)
    if status == 200:
        arch["srs"] = {
            "needs_review": body.get("needs_review"),
            "confidence": body.get("confidence"),
            "func_req": len(body.get("functional_requirements", []) or []),
        }
        print(f"[ARCH] SRS -> needs_review={body.get('needs_review')} "
              f"conf={body.get('confidence')} freq={len(body.get('functional_requirements', []) or [])}")
    else:
        print(f"[ARCH] SRS FAILED status={status} body={str(body)[:300]}")
    save_state(state)

    # ADR
    print("[ARCH] generating ADR (LLM) ...")
    status, body = api("POST", f"/documents/{full_id}/generate-adr", body={},
                       token=token, timeout=600)
    if status == 200:
        arch["adr"] = {"title": json.loads(body["adr_json"]).get("title", "?")[:60]}
        print(f"[ARCH] ADR -> {arch['adr']['title']}")
    else:
        print(f"[ARCH] ADR FAILED status={status} body={str(body)[:300]}")
    save_state(state)

    # Diagrams
    print("[ARCH] generating diagrams (LLM) ...")
    status, body = api("POST", f"/documents/{full_id}/generate-diagrams", body={},
                       token=token, timeout=600)
    if status == 200:
        created = body.get("created", [])
        ok = sum(1 for c in created if c["render_status"] == "ok")
        arch["diagrams"] = {"count": len(created), "rendered_ok": ok, "standard": body.get("standard_profile")}
        print(f"[ARCH] diagrams -> created={len(created)} rendered_ok={ok} "
              f"standard={body.get('standard_profile')}")
        for c in created:
            print(f"        {c['type']}: {c['render_status']}")
    else:
        print(f"[ARCH] diagrams FAILED status={status} body={str(body)[:300]}")
    save_state(state)

    # Coverage
    status, body = api("GET", f"/documents/{full_id}/coverage", token=token, timeout=30)
    if status == 200:
        arch["coverage"] = {
            "has_requirements": body.get("has_requirements"),
            "has_diagrams": body.get("has_diagrams"),
            "has_acceptance_criteria": body.get("has_acceptance_criteria"),
            "is_fully_covered": body.get("is_fully_covered"),
            "req_source": body.get("requirements_source"),
            "diagrams_count": body.get("diagrams_count"),
        }
        print(f"[ARCH] coverage -> full={body.get('is_fully_covered')} "
              f"req={body.get('has_requirements')} diag={body.get('has_diagrams')} "
              f"crit={body.get('has_acceptance_criteria')} source={body.get('requirements_source')}")
    else:
        print(f"[ARCH] coverage FAILED status={status}")
    save_state(state)

    # Exports
    status, _ = api("GET", f"/documents/{full_id}/export/markdown", token=token, timeout=60, raw=True)
    print(f"[ARCH] export markdown -> status={status}")
    status, _ = api("GET", f"/documents/{full_id}/export/docx", token=token, timeout=60, raw=True)
    print(f"[ARCH] export docx -> status={status}")
    status, _ = api("GET", f"/documents/{full_id}/export/full-package/docx", token=token, timeout=60, raw=True)
    print(f"[ARCH] export full-package docx -> status={status}")
    return state


def phase_audit_dashboard(token, state):
    """Check audit log and dashboard stats."""
    status, body = api("GET", "/audit/runs?limit=5", token=token, timeout=30)
    if status == 200:
        print(f"[AUDIT] {len(body)} recent runs")
        for r in body[:5]:
            print(f"  {r['action']}: provider={r.get('provider_used')} "
                  f"local={r.get('is_local_provider')} dur={r.get('duration_ms')}ms "
                  f"in={r.get('input_tokens')} out={r.get('output_tokens')}")
        state["audit"] = {"runs": len(body)}
    else:
        print(f"[AUDIT] FAILED status={status} body={str(body)[:200]}")
        # try alternate path
        status, body = api("GET", "/audit", token=token, timeout=30)
        print(f"[AUDIT] /audit status={status}")

    for path in ["/dashboard/stats-by-provider", "/dashboard/stats", "/dashboard/actual-usage"]:
        status, body = api("GET", path, token=token, timeout=30)
        print(f"[DASH] {path} -> status={status} body={str(body)[:150]}")
    return state


def phase_report():
    """Print consolidated test report."""
    state = load_state()
    print("\n" + "=" * 70)
    print("ИТОГОВЫЙ ОТЧЁТ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    ok = True

    docs = state.get("docs", {})
    print(f"\n1. Документы (загружено): {len(docs)} тем")
    for key, ids in docs.items():
        full = "OK" if "full_id" in ids else "MISSING"
        raw = "OK" if "raw_id" in ids else "MISSING"
        print(f"   - {key}: full={full} raw={raw}")

    print("\n2. Рецензии:")
    reviews = state.get("reviews", {})
    for key in sorted(reviews):
        r = reviews[key]
        print(f"   - {key}: needs_review={r['needs_review']} confidence={r['confidence']}")
    raw_keys = [k for k in reviews if k.endswith("_raw")]
    full_keys = [k for k in reviews if k.endswith("_full")]
    if raw_keys and all(reviews[k]["needs_review"] for k in raw_keys):
        print("   [PASS] все сырые ТЗ распознаны как требующие проверки")
    else:
        print("   [WARN] не все сырые ТЗ дали needs_review=true")
        ok = False
    if full_keys and all(not reviews[k]["needs_review"] for k in full_keys):
        print("   [PASS] все полные ТЗ рецензированы уверенно")
    else:
        print("   [INFO] часть полных ТЗ требует проверки (может быть нормой)")

    print("\n3. Пакетная рецензия:")
    batch = state.get("batch")
    if batch:
        print(f"   - status={batch['status']} total={batch['total']} "
              f"completed={batch['completed']} needs_review={batch['needs_review']} "
              f"errors={batch['errors']}")
    else:
        print("   [WARN] пакетная рецензия не выполнена")
        ok = False

    print("\n4. База знаний:")
    kb = state.get("kb_answers", [])
    if kb:
        for a in kb:
            print(f"   - {a['question'][:50]}... -> sources={a['sources']} conf={a['confidence']}")
    else:
        print("   [WARN] вопросы к БЗ не задавались")
        ok = False

    print("\n5. Уроки проекта:")
    lessons = state.get("lessons", [])
    if lessons:
        for l in lessons:
            print(f"   - {l['title'][:50]} source={l['source']}")
    else:
        print("   [WARN] уроки не созданы")
        ok = False

    print("\n6. Экономика:")
    econ = state.get("econ")
    if econ:
        print(f"   - project={econ.get('project_id','')[:8]}")
        print(f"   - hours={econ.get('total_hours')} conf={econ.get('confidence')}")
        print(f"   - capex={econ.get('capex')} opex={econ.get('opex_monthly')} "
              f"roi12m={econ.get('roi_12m_pct')} llm_source={econ.get('llm_cost_source')}")
    else:
        print("   [WARN] экономика не рассчитана")
        ok = False

    print("\n7. ArchStudio:")
    arch = state.get("arch")
    if arch:
        print(f"   - URS: {arch.get('urs')}")
        print(f"   - SRS: {arch.get('srs')}")
        print(f"   - ADR: {arch.get('adr')}")
        print(f"   - Diagrams: {arch.get('diagrams')}")
        print(f"   - Coverage: {arch.get('coverage')}")
    else:
        print("   [WARN] ArchStudio не прогнан")
        ok = False

    print("\n8. Аудит/Дашборд:")
    if state.get("audit"):
        print(f"   - audit runs: {state['audit']}")
    else:
        print("   [WARN] аудит не проверен")

    print("\n" + "=" * 70)
    print(f"ИТОГ: {'ВСЕ КЛЮЧЕВЫЕ СЦЕНАРИИ ПРОЙДЕНЫ' if ok else 'ЕСТЬ ПРОБЛЕМЫ (см. выше)'}")
    print("=" * 70)
    return 0 if ok else 1


def phase_reviews_one(token, state):
    """Run exactly ONE not-yet-done review (for incremental execution)."""
    docs = state.get("docs", {})
    reviews = state.setdefault("reviews", {})
    for key, cfg in DOCS.items():
        for kind in ("full", "raw"):
            idkey = f"{kind}_id"
            if key not in docs or idkey not in docs[key]:
                continue
            rkey = f"{key}_{kind}"
            if rkey in reviews:
                continue
            doc_id = docs[key][idkey]
            print(f"[REVIEW] {rkey} starting (doc={doc_id[:8]}) ...", flush=True)
            t0 = time.time()
            status, body = api("POST", f"/documents/{doc_id}/review", body={},
                               token=token, timeout=900)
            dt = round(time.time() - t0, 1)
            if status == 200:
                reviews[rkey] = {
                    "id": body["id"], "needs_review": body["needs_review"],
                    "confidence": body["confidence"],
                }
                rj = json.loads(body["review_json"])
                print(f"[REVIEW] {rkey} OK in {dt}s -> needs_review={body['needs_review']} "
                      f"confidence={body['confidence']} risks={len(rj.get('risks', []))} "
                      f"missing={len(rj.get('missing_requirements', []))} "
                      f"criteria={len(rj.get('acceptance_criteria', []))}", flush=True)
            else:
                print(f"[REVIEW] {rkey} FAILED status={status} body={str(body)[:300]}", flush=True)
            save_state(state)
            return state
    print("[REVIEW] all reviews already done", flush=True)
    return state


PHASES = {
    "auth": phase_auth,
    "upload": phase_upload,
    "reviews": phase_reviews,
    "review_one": phase_reviews_one,
    "batch": phase_batch,
    "kb": phase_kb_ask,
    "lessons": phase_lessons,
    "econ": phase_economics,
    "arch": phase_archstudio,
    "audit": phase_audit_dashboard,
    "report": phase_report,
}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "report"
    if which == "all":
        token = phase_auth()
        st = load_state()
        st = phase_upload(token, st)
        st = phase_reviews(token, st)
        st = phase_batch(token, st)
        st = phase_kb_ask(token, st)
        st = phase_lessons(token, st)
        st = phase_economics(token, st)
        st = phase_archstudio(token, st)
        st = phase_audit_dashboard(token, st)
        phase_report()
    elif which == "report":
        sys.exit(phase_report())
    else:
        fn = PHASES.get(which)
        if not fn:
            print(f"Unknown phase: {which}. Available: {', '.join(PHASES.keys())}")
            sys.exit(2)
        if which == "auth":
            fn()
        else:
            token = get_token()
            st = load_state()
            st = fn(token, st)
            save_state(st)