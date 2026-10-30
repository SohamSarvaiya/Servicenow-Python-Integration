"""OpenAI (ChatGPT), Anthropic (Claude), Google Gemini - sab plain REST se. Key server par save nahi hoti."""
import json
import re
import requests

DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-sonnet-4-6", "gemini": "gemini-2.0-flash"}


class LLMError(Exception):
    pass


def build_prompt(inc):
    return ("You are an ITSM assistant. Analyze this ServiceNow incident and reply ONLY with JSON having keys: "
            "summary (1-2 lines), category, priority (1-Critical..4-Low), root_cause_hypothesis, "
            "next_steps (list of 3 short strings).\n\n"
            f"Number: {inc.get('number')}\nShort description: {inc.get('short_description')}\n"
            f"Description: {inc.get('description')}\nCurrent priority: {inc.get('priority')}")


def _post(url, headers, payload):
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise LLMError(f"Network error: {e}") from e
    if r.status_code >= 400:
        raise LLMError(f"LLM API error {r.status_code}: {r.text[:200]}")
    return r.json()


def call_llm(provider, api_key, model, prompt):
    if not api_key:
        raise LLMError("API key missing hai. Settings me key daalo.")
    model = model or DEFAULT_MODELS.get(provider)
    if provider == "openai":
        j = _post("https://api.openai.com/v1/chat/completions",
                  {"Authorization": f"Bearer {api_key}"},
                  {"model": model, "messages": [{"role": "user", "content": prompt}]})
        return j["choices"][0]["message"]["content"]
    if provider == "anthropic":
        j = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                  {"model": model, "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]})
        return "".join(b.get("text", "") for b in j["content"])
    if provider == "gemini":
        j = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  {"x-goog-api-key": api_key},
                  {"contents": [{"parts": [{"text": prompt}]}]})
        return j["candidates"][0]["content"]["parts"][0]["text"]
    raise LLMError(f"Unknown provider: {provider}")


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {"summary": text}
    except json.JSONDecodeError:
        return {"summary": text}


def analyze_incident(provider, api_key, model, inc):
    return parse_json(call_llm(provider, api_key, model, build_prompt(inc)))
