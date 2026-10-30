import pytest
from app import servicenow, llm
from app.categorizer import categorize
from app.server import app


class FakeResp:
    def __init__(self, code=200, data=None):
        self.status_code, self._d, self.text = code, data or {}, str(data)
    def json(self):
        return self._d


def test_categorize_network_and_security():
    assert categorize("VPN connect nahi ho raha")["category"] == "Network"
    r = categorize("Suspicious phishing email")
    assert r["category"] == "Security" and r["suggested_priority"] == "1 - Critical"
    assert categorize("hello world")["category"] == "Other"


def test_basic_auth_list(monkeypatch):
    seen = {}
    def fake(method, url, **kw):
        seen.update(kw, url=url)
        return FakeResp(200, {"result": [{"number": "INC1"}]})
    monkeypatch.setattr(servicenow.requests, "request", fake)
    c = servicenow.ServiceNowClient("dev1.service-now.com", "u", "p")
    assert c.list_incidents(5)[0]["number"] == "INC1"
    assert seen["auth"] == ("u", "p") and seen["url"].startswith("https://dev1")


def test_error_mapping(monkeypatch):
    monkeypatch.setattr(servicenow.requests, "request", lambda *a, **k: FakeResp(401))
    with pytest.raises(servicenow.ServiceNowError, match="401"):
        servicenow.ServiceNowClient("x.com", "u", "p").get_incident("1")


def test_oauth_token(monkeypatch):
    monkeypatch.setattr(servicenow.requests, "post",
                        lambda *a, **k: FakeResp(200, {"access_token": "T", "expires_in": 100}))
    seen = {}
    def fake(method, url, **kw):
        seen.update(kw)
        return FakeResp(200, {"result": []})
    monkeypatch.setattr(servicenow.requests, "request", fake)
    servicenow.ServiceNowClient("x.com", "u", "p", "cid", "sec").list_incidents()
    assert seen["headers"]["Authorization"] == "Bearer T"


@pytest.mark.parametrize("provider,resp,url_part", [
    ("openai", {"choices": [{"message": {"content": '{"summary":"ok"}'}}]}, "openai.com"),
    ("anthropic", {"content": [{"text": '{"summary":"ok"}'}]}, "anthropic.com"),
    ("gemini", {"candidates": [{"content": {"parts": [{"text": '{"summary":"ok"}'}]}}]}, "googleapis.com"),
])
def test_llm_providers(monkeypatch, provider, resp, url_part):
    calls = []
    def fake(url, **kw):
        calls.append(url)
        return FakeResp(200, resp)
    monkeypatch.setattr(llm.requests, "post", fake)
    out = llm.analyze_incident(provider, "key", "", {"number": "INC1"})
    assert out["summary"] == "ok" and url_part in calls[0]


def test_llm_needs_key():
    with pytest.raises(llm.LLMError):
        llm.call_llm("openai", "", "", "hi")


def test_api_demo_flow():
    c = app.test_client()
    cfg = {"demo": True}
    rows = c.post("/api/incidents/list", json={"config": cfg}).get_json()["incidents"]
    assert len(rows) >= 9 and "rule" in rows[0]
    new = c.post("/api/incidents/create", json={"config": cfg, "data": {"short_description": "VPN down"}}).get_json()
    upd = c.post("/api/incidents/update", json={"config": cfg, "sys_id": new["incident"]["sys_id"],
                                                "data": {"state": "Resolved"}}).get_json()
    assert upd["incident"]["state"] == "Resolved"
    assert c.post("/api/ai", json={"llm": {"provider": "openai", "api_key": ""}, "incident": {}}).status_code == 400
