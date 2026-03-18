import json
import os
import re
from datetime import datetime

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()

LEADS_FILE = "/home/clarence/pizza-ranch-demo/leads.json"


def load_leads() -> list[dict]:
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE, "r") as f:
        return json.load(f)


def save_leads(leads: list[dict]):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = (
    "You are Ranger, a friendly and enthusiastic virtual assistant for Pizza Ranch "
    "FunZone in McPherson, Kansas. You help guests with menu information, buffet hours "
    "and pricing, FunZone arcade details, token pricing, birthday party bookings, and "
    "general questions.\n\n"
    "Restaurant details:\n"
    "- Name: Pizza Ranch FunZone\n"
    "- Address: 206 N Main St, McPherson, KS 67460\n"
    "- Phone: (620) 798-4262\n"
    "- Hours: Monday-Thursday 11AM-8PM, Friday-Saturday 11AM-8:30PM, Sunday 11AM-8PM\n"
    "- Menu: Pizza buffet, The Country's Best Chicken, salad bar, mashed potatoes, "
    "pasta, dessert pizza. Full menu available for curbside carryout.\n"
    "- Buffet Pricing: Adults $12.99, Kids 4-12 $7.99, Kids under 4 free. Includes "
    "unlimited drinks.\n"
    "- Buffet Hours: Lunch 11AM-2PM daily, Dinner 5PM-8PM daily\n"
    "- FunZone Arcade: Open same hours as restaurant, loaded with games and prizes for "
    "kids and adults\n"
    "- Tokens: 25 tokens $5, 75 tokens $15, 200 tokens $20\n"
    "- Game Cards: $10, $20, $50 loaded game cards available\n"
    "- Birthday & Group Parties: Party rooms seat up to 60 guests, free to reserve when "
    "all guests purchase buffet. Perfect for birthdays, church groups, school groups, "
    "team celebrations, family reunions.\n"
    "- Community Events: Pizza Ranch hosts Community Impact fundraiser events for local "
    "nonprofits and school groups. Contact us to host your own.\n"
    "- Hiring: Pizza Ranch McPherson is currently hiring. Apply in person or call.\n\n"
    "Your personality: energetic, friendly, and fun. Great with families and kids. "
    "Never make up information. If a guest asks something you cannot answer, collect "
    "their name and phone number and tell them a team member will follow up within "
    "1 business day. Keep all responses concise and under 80 words. Only provide "
    "information explicitly listed above."
)

HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pizza Ranch FunZone - McPherson, KS</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #FFF8F0;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100dvh;
  }

  .chat-container {
    width: 100%;
    max-width: 460px;
    height: 100dvh;
    max-height: 700px;
    display: flex;
    flex-direction: column;
    background: #FFF8F0;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 8px 30px rgba(0,0,0,.12);
  }

  @media (max-width: 500px) {
    .chat-container { max-height: 100dvh; border-radius: 0; }
  }

  .header {
    background: #C8102E;
    color: #fff;
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-icon {
    width: 38px; height: 38px;
    background: #F5A800;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
  }

  .header-text h1 { font-size: 15px; font-weight: 600; }
  .header-text p  { font-size: 12px; color: rgba(255,255,255,.7); margin-top: 2px; }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .bubble {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.5;
    word-wrap: break-word;
    white-space: pre-wrap;
  }

  .bubble .timestamp {
    display: block;
    text-align: right;
    font-size: 0.7rem;
    opacity: 0.6;
    margin-top: 4px;
  }

  .bubble.bot {
    align-self: flex-start;
    background: #FFF0E0;
    color: #2b2b2b;
    border-bottom-left-radius: 4px;
    white-space: normal;
  }

  .bubble.bot ul {
    margin: 4px 0;
    padding-left: 18px;
  }

  .bubble.bot li {
    margin: 2px 0;
  }

  .bubble.user {
    align-self: flex-end;
    background: #C8102E;
    color: #fff;
    border-bottom-right-radius: 4px;
  }

  .typing {
    align-self: flex-start;
    display: none;
    gap: 5px;
    padding: 12px 16px;
    background: #FFF0E0;
    border-radius: 16px;
    border-bottom-left-radius: 4px;
  }

  .typing.visible { display: flex; }

  .typing span {
    width: 7px; height: 7px;
    background: #C8102E;
    border-radius: 50%;
    animation: bounce .6s infinite alternate;
  }
  .typing span:nth-child(2) { animation-delay: .15s; }
  .typing span:nth-child(3) { animation-delay: .3s; }

  @keyframes bounce {
    to { opacity: .3; transform: translateY(-4px); }
  }

  .input-area {
    display: flex;
    padding: 12px;
    gap: 8px;
    border-top: 1px solid #f0e0cc;
    background: #FFF8F0;
  }

  .input-area input {
    flex: 1;
    border: 1px solid #e0d0c0;
    border-radius: 24px;
    padding: 10px 16px;
    font-size: 14px;
    outline: none;
    background: #fff;
  }

  .input-area input:focus { border-color: #F5A800; }

  .input-area button {
    width: 42px; height: 42px;
    border: none;
    border-radius: 50%;
    background: #F5A800;
    color: #fff;
    font-size: 18px;
    cursor: pointer;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background .2s;
  }

  .input-area button:hover { background: #e09800; }
  .input-area button:disabled { opacity: .5; cursor: default; }

  .quick-replies {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 4px 0 6px;
    align-self: flex-start;
  }

  .quick-replies button {
    background: transparent;
    border: 1.5px solid #F5A800;
    color: #F5A800;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 13px;
    cursor: pointer;
    transition: background .2s, color .2s;
    white-space: nowrap;
  }

  .quick-replies button:hover {
    background: #F5A800;
    color: #2b2b2b;
  }
</style>
</head>
<body>
<div class="chat-container">
  <div class="header">
    <div class="header-icon">&#127829;</div>
    <div class="header-text">
      <h1>Pizza Ranch FunZone - McPherson, KS</h1>
      <p>Ranger &#129312; &middot; Online</p>
    </div>
  </div>

  <div class="messages" id="messages">
    <div class="bubble bot">Howdy! I'm Ranger, your virtual assistant at Pizza Ranch FunZone in McPherson! Whether you need info on our buffet, arcade tokens, or party rooms, I'm here to help. What can I do for you today?</div>
    <div class="typing" id="typing"><span></span><span></span><span></span></div>
  </div>

  <div class="input-area">
    <input type="text" id="input" placeholder="Type a message..." autocomplete="off">
    <button id="send" aria-label="Send">&#10148;</button>
  </div>
</div>

<script>
const messagesEl = document.getElementById("messages");
const inputEl    = document.getElementById("input");
const sendBtn    = document.getElementById("send");
const typingEl   = document.getElementById("typing");

let history = [];
let busy = false;
let awaitingContact = false;
let lastBotContext = "";

function formatTime() {
  const now = new Date();
  let h = now.getHours();
  const m = String(now.getMinutes()).padStart(2, "0");
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return h + ":" + m + " " + ampm;
}

function renderMarkdown(text) {
  // Escape HTML entities first
  let html = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // Bold: **text**
  html = html.replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>");
  // Split into lines for list processing
  const lines = html.split("\\n");
  let result = [];
  let inList = false;
  for (const line of lines) {
    const li = line.match(/^[\\*\\+]\\s+(.+)/);
    if (li) {
      if (!inList) { result.push("<ul>"); inList = true; }
      result.push("<li>" + li[1] + "</li>");
    } else {
      if (inList) { result.push("</ul>"); inList = false; }
      result.push(line);
    }
  }
  if (inList) result.push("</ul>");
  return result.join("<br>").replace(/<br><ul>/g, "<ul>").replace(/<\\/ul><br>/g, "</ul>");
}

function addBubble(text, role) {
  removeQuickReplies();
  const d = document.createElement("div");
  d.className = "bubble " + (role === "user" ? "user" : "bot");
  const msgSpan = document.createElement("span");
  if (role === "user") {
    msgSpan.textContent = text;
  } else {
    msgSpan.innerHTML = renderMarkdown(text);
  }
  const ts = document.createElement("span");
  ts.className = "timestamp";
  ts.textContent = formatTime();
  d.appendChild(msgSpan);
  d.appendChild(ts);
  messagesEl.insertBefore(d, typingEl);
  if (role !== "user") showQuickReplies();
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function extractPhone(text) {
  const m = text.replace(/[^0-9]/g, "");
  if (m.length >= 10) return m.slice(0, 10);
  return null;
}

function extractName(messages) {
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === "user") {
      const t = msg.content.trim();
      const words = t.split(/\\s+/);
      if (words.length >= 1 && words.length <= 3 && !t.includes("?") && !extractPhone(t)) {
        return t;
      }
    }
  }
  return "";
}

async function send() {
  const text = inputEl.value.trim();
  if (!text || busy) return;

  busy = true;
  sendBtn.disabled = true;
  inputEl.value = "";
  addBubble(text, "user");
  history.push({ role: "user", content: text });

  const phone = extractPhone(text);
  if (awaitingContact && phone) {
    typingEl.classList.add("visible");
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const name = extractName(history.slice(0, -1)) || text.replace(/[0-9()\\-\\s]/g, "").trim() || "Unknown";
    try {
      await fetch("/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, phone: phone, context: lastBotContext })
      });
    } catch {}
    const thanks = "Thank you! A team member will reach out to you within 1 business day.";
    history.push({ role: "assistant", content: thanks });
    addBubble(thanks, "bot");
    awaitingContact = false;
    lastBotContext = "";
    typingEl.classList.remove("visible");
    busy = false;
    sendBtn.disabled = false;
    inputEl.focus();
    return;
  }

  typingEl.classList.add("visible");
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: history.slice(0, -1) })
    });
    const data = await res.json();
    const reply = data.reply || "Sorry, something went wrong.";
    history.push({ role: "assistant", content: reply });
    addBubble(reply, "bot");
    if (reply.includes("Could you share your name and phone number?")) {
      awaitingContact = true;
      lastBotContext = reply.split("\\n\\n")[0];
    }
  } catch {
    addBubble("Unable to reach the server. Please try again.", "bot");
  } finally {
    typingEl.classList.remove("visible");
    busy = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

function removeQuickReplies() {
  const old = document.getElementById("quickReplies");
  if (old) old.remove();
}

function showQuickReplies() {
  removeQuickReplies();
  const row = document.createElement("div");
  row.className = "quick-replies";
  row.id = "quickReplies";
  ["Buffet Hours & Pricing", "Token Prices", "Party Rooms", "Menu"].forEach(label => {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.addEventListener("click", () => {
      if (busy) return;
      removeQuickReplies();
      inputEl.value = label;
      send();
    });
    row.appendChild(btn);
  });
  messagesEl.insertBefore(row, typingEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", e => { if (e.key === "Enter") send(); });

showQuickReplies();
inputEl.focus();
</script>
</body>
</html>
"""


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class LeadRequest(BaseModel):
    name: str
    phone: str
    context: str


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


def clean_response(text: str) -> str:
    # Remove anything from ### onward
    text = re.split(r'###', text)[0]
    # Remove lines that look like prompt leakage (contain "Instruction" or "System")
    lines = text.splitlines()
    lines = [l for l in lines if not re.search(r'\b(Instruction|System|INST|<<SYS>>)\b', l, re.IGNORECASE)]
    return '\n'.join(lines).strip()


def has_factual_answer(text: str) -> bool:
    indicators = [
        "11am", "8pm", "8:30pm", "2pm", "5pm", "monday", "friday", "sunday",
        "$12.99", "$7.99", "under 4 free",
        "$5", "$15", "$20", "$10", "$50",
        "25 tokens", "75 tokens", "200 tokens",
        "60 guests", "620", "206 n main",
        "pizza buffet", "chicken", "salad bar", "dessert pizza",
        "game card",
    ]
    return any(i.lower() in text.lower() for i in indicators)


CONTACT_PROMPT = (
    "\n\nI'd love to have someone from our team follow up with you directly! "
    "Could you share your name and phone number? A team member will reach out "
    "within 1 business day."
)


@app.post("/chat")
async def chat(req: ChatRequest):
    history = req.history[-6:] if len(req.history) > 6 else req.history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.message})

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            OLLAMA_URL,
            json={"model": MODEL, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()

    reply = data.get("message", {}).get("content", "I'm sorry, I couldn't process that.")
    reply = clean_response(reply)
    if not has_factual_answer(reply):
        reply += CONTACT_PROMPT
    return {"reply": reply}


@app.post("/lead")
async def capture_lead(lead: LeadRequest):
    leads = load_leads()
    leads.append({
        "name": lead.name,
        "phone": lead.phone,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "context": lead.context,
    })
    save_leads(leads)
    return {"status": "ok"}


@app.delete("/admin/clear")
async def clear_leads(password: str = Query(...)):
    if password != "ranch2026":
        return JSONResponse(status_code=403, content={"error": "unauthorized"})
    save_leads([])
    return {"status": "cleared"}


ADMIN_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pizza Ranch FunZone - Admin</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #1e1e1e;
    color: #eee;
    padding: 32px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }
  h1 { font-size: 22px; color: #F5A800; }
  .subtitle { font-size: 13px; color: #888; margin-top: 4px; }
  .clear-btn {
    background: #C8102E;
    color: #fff;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }
  .clear-btn:hover { background: #a00d24; }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #2b2b2b;
    border-radius: 10px;
    overflow: hidden;
  }
  th {
    background: #333;
    color: #F5A800;
    padding: 14px 16px;
    text-align: left;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  td {
    padding: 12px 16px;
    border-top: 1px solid #3a3a3a;
    font-size: 14px;
    color: #ddd;
  }
  tr:hover td { background: #333; }
  .empty { text-align: center; padding: 40px; color: #666; font-size: 15px; }
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>Pizza Ranch FunZone - Captured Leads</h1>
      <p class="subtitle">LEAD_COUNT lead(s) collected</p>
    </div>
    <button class="clear-btn" onclick="clearAll()">Clear All</button>
  </div>
  LEAD_TABLE
<script>
async function clearAll() {
  if (!confirm("Delete all leads?")) return;
  const params = new URLSearchParams(window.location.search);
  await fetch("/admin/clear?password=" + params.get("password"), { method: "DELETE" });
  location.reload();
}
</script>
</body>
</html>
"""


@app.get("/admin", response_class=HTMLResponse)
async def admin(password: str = Query(...)):
    if password != "ranch2026":
        return HTMLResponse("<h1>Unauthorized</h1>", status_code=403)
    leads = load_leads()
    if not leads:
        table = '<p class="empty">No leads captured yet.</p>'
    else:
        rows = ""
        for lead in reversed(leads):
            rows += (
                f"<tr><td>{lead.get('name', '-')}</td>"
                f"<td>{lead.get('phone', '-')}</td>"
                f"<td>{lead.get('timestamp', '-')}</td>"
                f"<td>{lead.get('context', '-')}</td></tr>"
            )
        table = (
            "<table><thead><tr>"
            "<th>Name</th><th>Phone</th><th>Date/Time</th><th>Context</th>"
            "</tr></thead><tbody>" + rows + "</tbody></table>"
        )
    html = ADMIN_PAGE.replace("LEAD_TABLE", table).replace("LEAD_COUNT", str(len(leads)))
    return html
