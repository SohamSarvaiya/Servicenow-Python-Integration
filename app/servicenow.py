"""ServiceNow Table API client (Basic Auth + OAuth password grant) aur Demo client."""
import time
import requests

FIELDS = ("sys_id,number,short_description,description,state,priority,urgency,impact,"
          "category,assignment_group,caller_id,opened_at,sys_updated_on")


class ServiceNowError(Exception):
    pass


class ServiceNowClient:
    def __init__(self, instance, username="", password="", client_id="", client_secret="", timeout=20):
        if not instance:
            raise ServiceNowError("Instance URL required hai.")
        instance = instance.strip().rstrip("/")
        self.base = instance if instance.startswith("http") else f"https://{instance}"
        self.username, self.password = username, password
        self.client_id, self.client_secret = client_id, client_secret
        self.timeout = timeout
        self._token, self._exp = None, 0

    def _get_token(self):
        if self._token and time.time() < self._exp - 30:
            return self._token
        r = requests.post(f"{self.base}/oauth_token.do", timeout=self.timeout, data={
            "grant_type": "password", "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username, "password": self.password})
        if r.status_code != 200:
            raise ServiceNowError(f"OAuth fail ({r.status_code})")
        j = r.json()
        self._token, self._exp = j["access_token"], time.time() + int(j.get("expires_in", 1800))
        return self._token

    def _request(self, method, path, **kw):
        kw.setdefault("timeout", self.timeout)
        headers = {"Accept": "application/json"}
        if self.client_id:
            headers["Authorization"] = f"Bearer {self._get_token()}"
        else:
            kw["auth"] = (self.username, self.password)
        try:
            r = requests.request(method, f"{self.base}{path}", headers=headers, **kw)
        except requests.RequestException as e:
            raise ServiceNowError(f"Network error: {e}") from e
        if r.status_code == 401:
            raise ServiceNowError("Authentication fail (401). Username/Password check karo.")
        if r.status_code == 403:
            raise ServiceNowError("Permission nahi hai (403). Role/ACL check karo.")
        if r.status_code >= 400:
            raise ServiceNowError(f"ServiceNow error {r.status_code}: {r.text[:200]}")
        return r.json().get("result")

    def list_incidents(self, limit=20, query=""):
        params = {"sysparm_limit": limit, "sysparm_fields": FIELDS,
                  "sysparm_display_value": "true", "sysparm_query": query or "ORDERBYDESCsys_updated_on"}
        return self._request("GET", "/api/now/table/incident", params=params)

    def get_incident(self, sys_id):
        return self._request("GET", f"/api/now/table/incident/{sys_id}",
                             params={"sysparm_display_value": "true"})

    def create_incident(self, data):
        return self._request("POST", "/api/now/table/incident", json=data)

    def update_incident(self, sys_id, data):
        return self._request("PATCH", f"/api/now/table/incident/{sys_id}", json=data)


class DemoClient:
    """Bina ServiceNow instance ke app try karne ke liye in-memory data."""
    _SEED = [
        ("INC0010001", "VPN connect nahi ho raha, timeout error", "2 - High", "In Progress"),
        ("INC0010002", "Outlook email sync issue on laptop", "3 - Moderate", "New"),
        ("INC0010003", "Production database slow, queries timeout", "1 - Critical", "New"),
        ("INC0010004", "Printer floor 3 offline, paper jam", "4 - Low", "On Hold"),
        ("INC0010005", "Password reset required, account locked", "3 - Moderate", "New"),
        ("INC0010006", "Software install request: Adobe Reader", "4 - Low", "New"),
        ("INC0010007", "Wifi disconnecting frequently in meeting room", "2 - High", "In Progress"),
        ("INC0010008", "Suspicious phishing email reported by user", "1 - Critical", "New"),
        ("INC0010009", "Server disk space 95% full on app-srv-02", "2 - High", "New"),
    ]

    def __init__(self):
        self.rows = [{"sys_id": f"demo{i:03d}", "number": n, "short_description": s,
                      "description": f"{s}. User ne report kiya, details pending.",
                      "priority": p, "state": st, "category": "", "caller_id": "Demo User",
                      "assignment_group": "Service Desk", "opened_at": "2026-10-2%d 10:15:00" % (i % 9),
                      "sys_updated_on": "2026-10-30 09:00:00"}
                     for i, (n, s, p, st) in enumerate(self._SEED, 1)]

    def list_incidents(self, limit=20, query=""):
        q = (query or "").lower()
        rows = [r for r in self.rows if q in r["short_description"].lower() or q in r["number"].lower()]
        return rows[:limit]

    def get_incident(self, sys_id):
        for r in self.rows:
            if r["sys_id"] == sys_id:
                return r
        raise ServiceNowError("Incident nahi mila.")

    def create_incident(self, data):
        n = len(self.rows) + 1
        row = {"sys_id": f"demo{n:03d}", "number": f"INC00100{n:02d}", "state": "New",
               "priority": data.get("priority", "3 - Moderate"), "category": data.get("category", ""),
               "short_description": data.get("short_description", ""),
               "description": data.get("description", ""), "caller_id": "Demo User",
               "assignment_group": "Service Desk", "opened_at": "2026-10-30 10:00:00",
               "sys_updated_on": "2026-10-30 10:00:00"}
        self.rows.insert(0, row)
        return row

    def update_incident(self, sys_id, data):
        r = self.get_incident(sys_id)
        r.update({k: v for k, v in data.items() if v not in (None, "")})
        return r
