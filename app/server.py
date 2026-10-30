import os
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
from .servicenow import ServiceNowClient, DemoClient, ServiceNowError
from .categorizer import categorize_incident
from .llm import analyze_incident, LLMError

load_dotenv()
app = Flask(__name__, static_folder="static")
_demo = DemoClient()  # demo mode ka shared in-memory data


def get_client(cfg):
    cfg = cfg or {}
    if cfg.get("demo") or not (cfg.get("instance") or os.getenv("SERVICENOW_INSTANCE")):
        return _demo
    return ServiceNowClient(
        cfg.get("instance") or os.getenv("SERVICENOW_INSTANCE"),
        cfg.get("username") or os.getenv("SERVICENOW_USERNAME", ""),
        cfg.get("password") or os.getenv("SERVICENOW_PASSWORD", ""),
        cfg.get("client_id") or os.getenv("SERVICENOW_CLIENT_ID", ""),
        cfg.get("client_secret") or os.getenv("SERVICENOW_CLIENT_SECRET", ""))


def with_rules(inc):
    return {**inc, "rule": categorize_incident(inc)}


def handle(fn):
    def wrapper(*a, **kw):
        try:
            return jsonify(fn(request.get_json(silent=True) or {}))
        except (ServiceNowError, LLMError) as e:
            return jsonify({"error": str(e)}), 400
    wrapper.__name__ = fn.__name__
    return wrapper


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/incidents/list")
@handle
def list_inc(b):
    rows = get_client(b.get("config")).list_incidents(int(b.get("limit", 20)), b.get("query", ""))
    return {"incidents": [with_rules(r) for r in rows]}


@app.post("/api/incidents/create")
@handle
def create_inc(b):
    return {"incident": with_rules(get_client(b.get("config")).create_incident(b.get("data", {})))}


@app.post("/api/incidents/update")
@handle
def update_inc(b):
    return {"incident": with_rules(get_client(b.get("config")).update_incident(b["sys_id"], b.get("data", {})))}


@app.post("/api/ai")
@handle
def ai(b):
    l = b.get("llm", {})
    return {"analysis": analyze_incident(l.get("provider"), l.get("api_key"), l.get("model"), b.get("incident", {}))}


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5000)), debug=False)
