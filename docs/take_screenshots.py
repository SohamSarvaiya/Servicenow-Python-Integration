"""README ke screenshots banata hai. Chalane se pehle: python -m app.server  (port 5000)
Usage: pip install playwright && playwright install chromium && python docs/take_screenshots.py
NOTE: AI analysis screenshot me sample response mock hai (real key use nahi hoti)."""
import json
from playwright.sync_api import sync_playwright

OUT = "docs/screenshots"
SAMPLE = {"analysis": {"summary": "Production database me slow queries ki wajah se application timeout ho rahe hain.",
          "category": "Database", "priority": "1-Critical",
          "root_cause_hypothesis": "Missing index ya long-running query se CPU/IO saturation.",
          "next_steps": ["Slow query log aur active sessions check karo", "Missing index add karo ya query optimize karo", "Fix ke baad monitoring aur stakeholders ko update do"]}}

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 860})
    pg.route("**/api/ai", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(SAMPLE)))
    pg.goto("http://127.0.0.1:5000"); pg.wait_for_selector("#rows tr", state="attached"); pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/01-dashboard.png")
    pg.click("nav button[data-s=inc]"); pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/02-incidents.png")
    pg.click("tr.r:nth-child(3)"); pg.evaluate("document.getElementById('key').value='demo'"); pg.click("text=AI Analyze"); pg.wait_for_selector(".ai")
    pg.screenshot(path=f"{OUT}/03-incident-detail-ai.png")
    pg.click(".close"); pg.click("nav button[data-s=set]"); pg.wait_for_timeout(200)
    pg.screenshot(path=f"{OUT}/04-settings.png")
    pg.click("nav button[data-s=inc]"); pg.click("#inc .tool button.pr"); pg.fill("#nsd", "Laptop keyboard kaam nahi kar raha")
    pg.fill("#nd", "Keyboard keys respond nahi kar rahi."); pg.wait_for_timeout(200)
    pg.screenshot(path=f"{OUT}/05-create-incident.png")
    b.close()
