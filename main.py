"""Web entry point for the Vera chat page and challenge API."""

import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from bot import app, call_llm

WEB_CHAT_DIR = Path(__file__).parent / "static"
WEB_CHAT_SESSIONS: dict[str, list[dict[str, str]]] = {}


class WebChatBody(BaseModel):
    session_id: str
    message: str


WEB_CHAT_SYSTEM = """You are Vera, a warm, practical AI assistant for magicpin merchants.
Help small business owners improve their magicpin listings, understand performance,
respond to reviews, and think through offers and customer engagement. Keep replies
clear, friendly, and concise. Ask one focused follow-up question when needed. Never
claim you can access a merchant account or invent performance figures, policies,
offers, or actions. If asked about account-specific data, explain that you cannot see
their account in this demo and ask them to share the relevant details. Do not claim
to send messages, edit listings, or make changes; offer a draft or guidance instead."""


def fallback_reply(message: str) -> str:
    text = message.lower()
    if any(word in text for word in ("hello", "hi", "hey", "namaste")):
        return "Hi! I’m Vera, your magicpin business assistant. I can help with your listing, reviews, offers, and customer messages. What would you like to work on?"
    if "review" in text:
        return "A good review reply is personal, brief, and specific. Thank the customer, address the point they raised, and invite them back. Share a review here and I can help draft a response."
    if "offer" in text or "discount" in text:
        return "A useful offer should be easy to understand and worthwhile for both you and your customer. What kind of business do you run, and which service or item would you like to feature?"
    if "listing" in text or "profile" in text:
        return "A clear listing helps customers decide quickly. Start with accurate hours, current photos, your most popular services, and any important booking details. What would you like to improve first?"
    return "I can help with your magicpin listing, reviews, offers, or customer messages. Tell me a little about your business and what you’re trying to do, and we’ll work through it together."


# bot.py includes these routes in the workspace copy; avoid registering duplicates
# when running that copy, while keeping this entry point compatible with GitHub.
if not any(route.path == "/" for route in app.routes):
    @app.get("/", include_in_schema=False)
    async def chat_home():
        return FileResponse(WEB_CHAT_DIR / "index.html")


if not any(route.path == "/chat" for route in app.routes):
    @app.post("/chat")
    async def web_chat(body: WebChatBody):
        message = body.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Please enter a message.")
        if len(message) > 2000:
            raise HTTPException(status_code=413, detail="Please keep your message under 2,000 characters.")
        if len(body.session_id) > 100:
            raise HTTPException(status_code=400, detail="Invalid session.")

        history = WEB_CHAT_SESSIONS.setdefault(body.session_id, [])
        history.append({"role": "user", "content": message})
        history[:] = history[-20:]
        transcript = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)
        answer = call_llm(WEB_CHAT_SYSTEM, transcript)
        answer = (answer or "").strip() or fallback_reply(message)
        history.append({"role": "assistant", "content": answer})
        history[:] = history[-20:]
        mode = "ai" if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") else "demo"
        return {"reply": answer, "mode": mode}
