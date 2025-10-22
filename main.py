# --- Team Orthonext (DEMO IN-MEMORY) ---
# Funziona su Render senza scrivere su disco: dati volatili finché il servizio resta attivo.
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional, Dict, List
from passlib.hash import bcrypt
import os, itertools

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET", "CAMBIA_QUESTA_STRINGA_LUNGA_RANDOM"))

# ===== CSS inline (niente /static) =====
BASE_CSS = """*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial,sans-serif;background:#f7f7fb;color:#111}
a{color:#0b66ff;text-decoration:none}.logo{font-weight:800;font-size:20px}.logo span{color:#0b66ff}
.container{max-width:980px;margin:0 auto;padding:16px}
.header{display:flex;justify-content:space-between;align-items:center;background:white;border-bottom:1px solid #e8e8ef}
.header nav a{margin-left:12px;padding:8px 10px;border-radius:8px}.header nav a.primary{background:#0b66ff;color:white}
.hero{padding:40px 0}
h1{font-size:36px;line-height:1.2}h2{margin-top:24px}
.button{display:inline-block;padding:10px 14px;border:1px solid #ddd;border-radius:8px;background:white}
.button.primary{background:#0b66ff;color:#fff;border-color:#0b66ff}.button.small{font-size:12px;padding:6px 8px}
.card{background:white;border:1px solid #e8e8ef;border-radius:10px;padding:16px;margin:10px 0}
.form label{display:block;margin-bottom:10px}.form input,.form textarea{width:100%;padding:10px;border:1px solid #ddd;border-radius:8px}
.error{background:#ffe9e9;border:1px solid #ffc2c2;padding:8px 10px;border-radius:8px;margin-bottom:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.search{display:flex;gap:8px;margin:10px 0}.search input{flex:1}
.bullets{line-height:1.9}
.footer{color:#666}
.inline{display:inline}
.stack .card{margin-bottom:8px}"""

def layout(user, content, title="Team Orthonext"):
    nav = (f'''
      <a href="/surgeons">Chirurghi</a>
      {'<a href="/inbox">Inbox</a><a href="/profile">Profilo</a><a href="/logout">Logout</a>' if user else '<a href="/login">Login</a><a class="primary" href="/register">Registrati</a>'}
    ''')
    return f"""<!doctype html><html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{BASE_CSS}</style></head>
<body>
<header class="container header"><a href="/" class="logo">Team <span>Orthonext</span></a><nav>{nav}</nav></header>
<main class="container">{content}</main>
<footer class="container footer"><small>© 2025 Orthonext • DEMO (dati non persistenti)</small></footer>
</body></html>"""

# ===== Storage in-memory =====
User = Dict[str, str]  # keys: id,email,full_name,hash,specialty,subs,region,city,hosp,languages,bio,availability
USERS: Dict[int, User] = {}
TEAM_LINKS: List[Dict[str,int]] = []  # {id, from_id, to_id, status}
_uid = itertools.count(1)
_linkid = itertools.count(1)

SESSION_KEY = "session_user_id"

def current_user(request: Request) -> Optional[User]:
    uid = request.session.get(SESSION_KEY)
    return USERS.get(uid) if uid else None

def require_login(request: Request) -> int:
    uid = request.session.get(SESSION_KEY)
    if not uid: raise HTTPException(status_code=401, detail="Login richiesto")
    return uid

# ===== Health =====
@app.get("/health", response_class=PlainTextResponse)
def health(): return "ok"

# ===== Home =====
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return layout(current_user(request), f"""
<section class="hero">
  <h1>Fai squadra con i migliori <em>chirurghi ortopedici</em>.</h1>
  <p>Registrati, crea il profilo e trova colleghi per sala operatoria e progetti.</p>
  {('<p><a class="button" href="/surgeons">Cerca colleghi</a> <a class="button" href="/inbox">Inbox inviti</a></p>' if current_user(request) else '<p><a class="button primary" href="/register">Crea il mio profilo</a></p>')}
</section>
""")

# ===== Auth =====
@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return layout(None, """
<h2>Registrati</h2>
<form method="post" class="card form">
  <label>Email<input type="email" name="email" required></label>
  <label>Nome e cognome<input type="text" name="full_name" required></label>
  <label>Password<input type="password" name="password" required></label>
  <button class="button primary" type="submit">Crea account</button>
  <p>Hai già un account? <a href="/login">Accedi</a></p>
</form>
""", "Registrazione — Team Orthonext")

@app.post("/register")
def register(request: Request, email: str = Form(...), full_name: str = Form(""), password: str = Form(...)):
    email = email.strip().lower()
    # check duplicate
    if any(u["email"] == email for u in USERS.values()):
        return HTMLResponse(layout(None, "<p class='card error'>Email già registrata.</p>"), status_code=400)
    uid = next(_uid)
    USERS[uid] = {
        "id": str(uid),
        "email": email,
        "full_name": full_name,
        "hash": bcrypt.hash(password),
        "specialty": "Ortopedia",
        "subs": "",
        "region": "",
        "city": "",
        "hosp": "",
        "languages": "Italiano, English",
        "bio": "",
        "availability": ""
    }
    request.session[SESSION_KEY] = uid
    return RedirectResponse(url="/onboarding", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return layout(None, """
<h2>Login</h2>
<form method="post" class="card form">
  <label>Email<input type="email" name="email" required></label>
  <label>Password<input type="password" name="password" required></label>
  <button class="button primary" type="submit">Accedi</button>
  <p>Nuovo qui? <a href="/register">Registrati</a></p>
</form>
""", "Login — Team Orthonext")

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    for uid, u in USERS.items():
        if u["email"] == email and bcrypt.verify(password, u["hash"]):
            request.session[SESSION_KEY] = uid
            return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(layout(None, "<p class='card error'>Credenziali non valide.</p>"), status_code=401)

@app.get("/logout")
def logout(request: Request):
    request.session.pop(SESSION_KEY, None)
    return RedirectResponse(url="/", status_code=303)

# ===== Onboarding / Profilo =====
def form_row(label, name, value="", type_="text"):
    if type_ == "textarea":
        return f'<label>{label}<textarea name="{name}" rows="4">{value or ""}</textarea></label>'
    return f'<label>{label}<input type="{type_}" name="{name}" value="{value or ""}"></label>'

@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_form(request: Request):
    uid = require_login(request)
    u = USERS[uid]
    content = f"""
<h2>Onboarding</h2>
<form method="post" class="card form">
  {form_row('Specialità principale','specialty', u['specialty'])}
  {form_row('Sottospecialità (virgole)','subs', u['subs'])}
  {form_row('Regione','region', u['region'])}
  {form_row('Città','city', u['city'])}
  {form_row('Ospedali / Strutture','hosp', u['hosp'])}
  {form_row('Lingue','languages', u['languages'])}
  <label>Disponibilità<textarea name="availability" rows="3">{u['availability']}</textarea></label>
  <label>Bio<textarea name="bio" rows="4">{u['bio']}</textarea></label>
  <button class="button primary" type="submit">Salva</button>
</form>"""
    return layout(u, content, "Onboarding — Team Orthonext")

@app.post("/onboarding")
def onboarding(request: Request,
               specialty: str = Form("Ortopedia"),
               subs: str = Form(""),
               region: str = Form(""),
               city: str = Form(""),
               hosp: str = Form(""),
               languages: str = Form("Italiano, English"),
               availability: str = Form(""),
               bio: str = Form("")):
    uid = require_login(request)
    u = USERS[uid]
    u.update(dict(specialty=specialty, subs=subs, region=region, city=city,
                  hosp=hosp, languages=languages, availability=availability, bio=bio))
    return RedirectResponse(url="/profile", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    uid = require_login(request)
    u = USERS[uid]
    content = f"""
<h2>Il mio profilo</h2>
<div class="card">
  <h3>{u['full_name']}</h3>
  <p><strong>Specialità:</strong> {u['specialty']}</p>
  <p><strong>Sottospecialità:</strong> {u['subs']}</p>
  <p><strong>Regione:</strong> {u['region']} — {u['city']}</p>
  <p><strong>Ospedali:</strong> {u['hosp']}</p>
  <p><strong>Lingue:</strong> {u['languages']}</p>
  <p><strong>Disponibilità:</strong> {u['availability']}</p>
  <p><strong>Bio:</strong> {u['bio']}</p>
</div>
<p><a class="button" href="/onboarding">Modifica</a></p>"""
    return layout(u, content, "Profilo — Team Orthonext")

# ===== Directory & Inviti (semplici) =====
@app.get("/surgeons", response_class=HTMLResponse)
def surgeons(request: Request, q: Optional[str] = None):
    me = current_user(request)
    lst = list(USERS.values())
    if q:
        ql = q.lower()
        lst = [u for u in lst if ql in (u["full_name"]+u["subs"]+u["region"]+u["city"]+u["hosp"]).lower()]
    cards = []
    for u in lst:
        invite = ""
        if me and me["id"] != u["id"]:
            invite = f"""
            <form method="post" action="/team/request">
              <input type="hidden" name="to_id" value="{u['id']}">
              <button class="button small">Invita nel mio team</button>
            </form>"""
        cards.append(f"""
        <div class="card">
          <h3>{u['full_name']}</h3>
          <p><strong>{u['specialty']}</strong> — {u['subs']}</p>
          <p>{u['region']} • {u['city']}</p>
          <p><small>Ospedali: {u['hosp']}</small></p>
          {invite}
        </div>""")
    content = f"""
<h2>Chirurghi</h2>
<form method="get" class="search">
  <input type="text" name="q" value="{q or ''}" placeholder="cerca per nome, regione, sottospecialità, ospedale…">
  <button class="button" type="submit">Cerca</button>
</form>
<div class="grid">{''.join(cards) if cards else '<p>Nessun risultato.</p>'}</div>"""
    return layout(me, content, "Chirurghi — Team Orthonext")

@app.post("/team/request")
def team_request(request: Request, to_id: int = Form(...)):
    uid = require_login(request)
    if str(uid) == str(to_id):
        raise HTTPException(status_code=400, detail="Non puoi invitare te stesso.")
    TEAM_LINKS.append({"id": next(_linkid), "from_id": uid, "to_id": int(to_id), "status": "pending"})
    return RedirectResponse(url="/inbox", status_code=303)

@app.post("/team/respond")
def team_respond(request: Request, link_id: int = Form(...), action: str = Form(...)):
    uid = require_login(request)
    for l in TEAM_LINKS:
        if l["id"] == link_id and l["to_id"] == uid:
            l["status"] = "accepted" if action == "accepted" else "declined"
            break
    return RedirectResponse(url="/inbox", status_code=303)

@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request):
    uid = require_login(request)
    me = USERS[uid]
    incoming = [l for l in TEAM_LINKS if l["to_id"] == uid]
    outgoing = [l for l in TEAM_LINKS if l["from_id"] == uid]
    def row_in(l):
        f = USERS.get(l["from_id"], {"full_name":"(utente)"})
        btns = "" if l["status"] != "pending" else f"""
        <form method="post" action="/team/respond" class="inline">
          <input type="hidden" name="link_id" value="{l['id']}">
          <button class="button small" name="action" value="accepted">Accetta</button>
          <button class="button small" name="action" value="declined">Rifiuta</button>
        </form>"""
        return f"""<div class="card"><p>Invito da <strong>{f['full_name']}</strong> — stato: <strong>{l['status']}</strong></p>{btns}</div>"""
    def row_out(l):
        t = USERS.get(l["to_id"], {"full_name":"(utente)"})
        return f"""<div class="card"><p>Hai invitato <strong>{t['full_name']}</strong> — stato: <strong>{l['status']}</strong></p></div>"""
    content = f"""
<h2>Inbox inviti</h2>
<h3>In arrivo</h3>
<div class="stack">{''.join(map(row_in, incoming)) or '<p>Nessun invito in arrivo.</p>'}</div>
<h3>Inviati</h3>
<div class="stack">{''.join(map(row_out, outgoing)) or '<p>Nessun invito inviato.</p>'}</div>"""
    return layout(me, content, "Inbox — Team Orthonext")
