# --- Team Orthonext: FastAPI single-file app (Render-ready) ---
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from sqlmodel import SQLModel, Field, Session, select, create_engine

from typing import Optional
from datetime import datetime
from passlib.hash import bcrypt
import os, pathlib

# ============================================================
# App & Config
# ============================================================

app = FastAPI()

# Secret per le sessioni (impostalo su Render: Environment -> APP_SECRET)
SECRET = os.getenv("APP_SECRET", "CAMBIA_QUESTA_STRINGA_LUNGA_RANDOM")
app.add_middleware(SessionMiddleware, secret_key=SECRET)

# ---- Static (usiamo /tmp che è scrivibile su Render) ----
STATIC_DIR = os.getenv("STATIC_DIR", "/tmp/static")
os.makedirs(STATIC_DIR, exist_ok=True)
css_path = os.path.join(STATIC_DIR, "style.css")
if not os.path.exists(css_path):
    try:
        with open(css_path, "w") as f:
            f.write("""*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial,sans-serif;background:#f7f7fb;color:#111}
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
.stack .card{margin-bottom:8px}""")
    except Exception:
        pass

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---- Database (Render-friendly) ----
# Se monti un Disk a /data su Render, imposta:
#   DATABASE_URL = sqlite:////data/db.sqlite3
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/db.sqlite3")

# Crea la cartella che contiene il file SQLite, se necessario
if DATABASE_URL.startswith("sqlite:////"):
    db_path = DATABASE_URL.replace("sqlite:////", "/")
elif DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
else:
    db_path = None
if db_path:
    pathlib.Path(os.path.dirname(db_path) or ".").mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# ============================================================
# Modelli
# ============================================================

class TeamLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    from_user_id: int = Field(foreign_key="user.id")
    to_user_id: int = Field(foreign_key="user.id")
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    full_name: str = Field(default="")
    specialty: str = Field(default="Ortopedia")
    sub_specialties: str = Field(default="")
    region: str = Field(default="")
    city: str = Field(default="")
    hospital_affiliations: str = Field(default="")
    languages: str = Field(default="Italiano, English")
    bio: str = Field(default="")
    availability: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================
# Auth utils
# ============================================================

SESSION_KEY = "session_user_id"

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.verify(pw, hashed)

def get_current_user_id(request: Request) -> Optional[int]:
    return request.session.get(SESSION_KEY)

def login_user(request: Request, user_id: int) -> None:
    request.session[SESSION_KEY] = user_id

def logout_user(request: Request) -> None:
    request.session.pop(SESSION_KEY, None)

def require_login(request: Request) -> int:
    uid = get_current_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Login richiesto")
    return uid

# ============================================================
# Startup
# ============================================================

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# ============================================================
# Template HTML basilare
# ============================================================

def layout(user, content, title="Team Orthonext"):
    nav = (f'''
      <a href="/surgeons">Chirurghi</a>
      {'<a href="/inbox">Inbox</a><a href="/profile">Profilo</a><a href="/logout">Logout</a>' if user else '<a href="/login">Login</a><a class="primary" href="/register">Registrati</a>'}
    ''')
    return f"""<!doctype html><html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/style.css"></head>
<body>
<header class="container header"><a href="/" class="logo">Team <span>Orthonext</span></a><nav>{nav}</nav></header>
<main class="container">{content}</main>
<footer class="container footer"><small>© 2025 Orthonext • GDPR-friendly MVP</small></footer>
</body></html>"""

def home_tpl(user):
    return f"""
<section class="hero">
  <h1>Fai squadra con i migliori <em>chirurghi ortopedici</em>.</h1>
  <p>Registrati, crea il profilo e trova colleghi per sala operatoria e progetti.</p>
  {('<p><a class="button" href="/surgeons">Cerca colleghi</a> <a class="button" href="/inbox">Inbox inviti</a></p>' if user else '<p><a class="button primary" href="/register">Crea il mio profilo</a></p>')}
</section>"""

def form_row(label, name, value="", type_="text"):
    if type_ == "textarea":
        return f'<label>{label}<textarea name="{name}" rows="4">{value or ""}</textarea></label>'
    return f'<label>{label}<input type="{type_}" name="{name}" value="{value or ""}"></label>'

# ============================================================
# Rotte principali
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    uid = get_current_user_id(request)
    user = None
    if uid:
        with Session(engine) as s:
            user = s.get(User, uid)
    return layout(user, home_tpl(user))

@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    content = """
<h2>Registrati</h2>
<form method="post" class="card form">
  <label>Email<input type="email" name="email" required></label>
  <label>Nome e cognome<input type="text" name="full_name" required></label>
  <label>Password<input type="password" name="password" required></label>
  <button class="button primary" type="submit">Crea account</button>
  <p>Hai già un account? <a href="/login">Accedi</a></p>
</form>"""
    return layout(None, content, "Registrazione — Team Orthonext")

@app.post("/register")
def register(request: Request, email: str = Form(...), full_name: str = Form(""), password: str = Form(...)):
    email = email.strip().lower()
    with Session(engine) as s:
        exists = s.exec(select(User).where(User.email == email)).first()
        if exists:
            return HTMLResponse(layout(None, "<p class='card error'>Email già registrata.</p>"), status_code=400)
        user = User(email=email, full_name=full_name, password_hash=hash_password(password))
        s.add(user); s.commit(); s.refresh(user)
        login_user(request, user.id)
    return RedirectResponse(url="/onboarding", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    content = """
<h2>Login</h2>
<form method="post" class="card form">
  <label>Email<input type="email" name="email" required></label>
  <label>Password<input type="password" name="password" required></label>
  <button class="button primary" type="submit">Accedi</button>
  <p>Nuovo qui? <a href="/register">Registrati</a></p>
</form>"""
    return layout(None, content, "Login — Team Orthonext")

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    with Session(engine) as s:
        user = s.exec(select(User).where(User.email == email)).first()
        if not user or not verify_password(password, user.password_hash):
            return HTMLResponse(layout(None, "<p class='card error'>Credenziali non valide.</p>"), status_code=401)
        login_user(request, user.id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse(url="/", status_code=303)

# ============================================================
# Profilo / Onboarding / Directory
# ============================================================

@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_form(request: Request):
    uid = get_current_user_id(request)
    if not uid:
        return RedirectResponse(url="/login", status_code=303)
    with Session(engine) as s:
        user = s.get(User, uid)
    content = f"""
<h2>Onboarding</h2>
<form method="post" class="card form">
  {form_row('Specialità principale','specialty', user.specialty)}
  {form_row('Sottospecialità (virgole)','sub_specialties', user.sub_specialties)}
  {form_row('Regione','region', user.region)}
  {form_row('Città','city', user.city)}
  {form_row('Ospedali / Strutture','hospital_affiliations', user.hospital_affiliations)}
  {form_row('Lingue','languages', user.languages)}
  <label>Disponibilità<textarea name="availability" rows="3">{user.availability or ''}</textarea></label>
  <label>Bio<textarea name="bio" rows="4">{user.bio or ''}</textarea></label>
  <button class="button primary" type="submit">Salva</button>
</form>"""
    return layout(user, content, "Onboarding — Team Orthonext")

@app.post("/onboarding")
def onboarding(request: Request,
               specialty: str = Form("Ortopedia"),
               sub_specialties: str = Form(""),
               region: str = Form(""),
               city: str = Form(""),
               hospital_affiliations: str = Form(""),
               languages: str = Form("Italiano, English"),
               availability: str = Form(""),
               bio: str = Form("")):
    uid = require_login(request)
    with Session(engine) as s:
        user = s.get(User, uid)
        user.specialty = specialty
        user.sub_specialties = sub_specialties
        user.region = region
        user.city = city
        user.hospital_affiliations = hospital_affiliations
        user.languages = languages
        user.availability = availability
        user.bio = bio
        s.add(user); s.commit()
    return RedirectResponse(url="/profile", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
def my_profile(request: Request):
    uid = require_login(request)
    with Session(engine) as s:
        user = s.get(User, uid)
    content = f"""
<h2>Il mio profilo</h2>
<div class="card">
  <h3>{user.full_name}</h3>
  <p><strong>Specialità:</strong> {user.specialty}</p>
  <p><strong>Sottospecialità:</strong> {user.sub_specialties}</p>
  <p><strong>Regione:</strong> {user.region} — {user.city}</p>
  <p><strong>Ospedali:</strong> {user.hospital_affiliations}</p>
  <p><strong>Lingue:</strong> {user.languages}</p>
  <p><strong>Disponibilità:</strong> {user.availability}</p>
  <p><strong>Bio:</strong> {user.bio}</p>
</div>
<p><a class="button" href="/onboarding">Modifica</a></p>"""
    return layout(user, content, "Profilo — Team Orthonext")

@app.get("/surgeons", response_class=HTMLResponse)
def surgeons_list(request: Request, q: Optional[str] = None):
    uid = get_current_user_id(request)
    with Session(engine) as s:
        stmt = select(User)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where((User.full_name.ilike(like)) |
                              (User.sub_specialties.ilike(like)) |
                              (User.region.ilike(like)) |
                              (User.city.ilike(like)) |
                              (User.hospital_affiliations.ilike(like)))
        users = s.exec(stmt.order_by(User.created_at.desc())).all()
        me = s.get(User, uid) if uid else None
    cards = []
    for u in users:
        invite = f"""
        <form method="post" action="/team/request">
          <input type="hidden" name="to_user_id" value="{u.id}">
          <button class="button small">Invita nel mio team</button>
        </form>""" if me and me.id != u.id else ""
        cards.append(f"""
        <div class="card">
          <h3><a href="/user/{u.id}">{u.full_name}</a></h3>
          <p><strong>{u.specialty}</strong> — {u.sub_specialties}</p>
          <p>{u.region} • {u.city}</p>
          <p><small>Ospedali: {u.hospital_affiliations}</small></p>
          {invite}
        </div>""")
    content = f"""
<h2>Chirurghi</h2>
<form method="get" class="search">
  <input type="text" name="q" value="{q or ''}" placeholder="cerca per nome, regione, sottospecialità, ospedale…">
  <button class="button" type="submit">Cerca</button>
</form>
<div class="grid">{''.join(cards)}</div>"""
    return layout(me, content, "Chirurghi — Team Orthonext")

# ============================================================
# Team: inviti & Inbox
# ============================================================

@app.post("/team/request")
def team_request(request: Request, to_user_id: int = Form(...)):
    uid = require_login(request)
    if uid == to_user_id:
        raise HTTPException(status_code=400, detail="Non puoi invitare te stesso.")
    with Session(engine) as s:
        link = TeamLink(from_user_id=uid, to_user_id=to_user_id, status="pending")
        s.add(link); s.commit()
    return RedirectResponse(url="/inbox", status_code=303)

@app.post("/team/respond")
def team_respond(request: Request, link_id: int = Form(...), action: str = Form(...)):
    uid = require_login(request)
    with Session(engine) as s:
        link = s.get(TeamLink, link_id)
        if not link or link.to_user_id != uid:
            raise HTTPException(status_code=404, detail="Richiesta non trovata.")
        if action not in ["accepted", "declined"]:
            raise HTTPException(status_code=400, detail="Azione non valida.")
        link.status = action
        s.add(link); s.commit()
    return RedirectResponse(url="/inbox", status_code=303)

@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request):
    uid = require_login(request)
    with Session(engine) as s:
        incoming = s.exec(
            select(TeamLink).where(TeamLink.to_user_id == uid).order_by(TeamLink.created_at.desc())
        ).all()
        outgoing = s.exec(
            select(TeamLink).where(TeamLink.from_user_id == uid).order_by(TeamLink.created_at.desc())
        ).all()
        me = s.get(User, uid)

    def row_in(l):
        return f"""<div class="card">
        <p>Invito da <a href="/user/{l.from_user_id}">#{l.from_user_id}</a> — stato: <strong>{l.status}</strong></p>
        {('<form method="post" action="/team/respond"><input type="hidden" name="link_id" value="'+str(l.id)+'"><button class="button small" name="action" value="accepted">Accetta</button> <button class="button small" name="action" value="declined">Rifiuta</button></form>' if l.status=='pending' else '')}
        </div>"""

    def row_out(l):
        return f"""<div class="card">
        <p>Hai invitato <a href="/user/{l.to_user_id}">#{l.to_user_id}</a> — stato: <strong>{l.status}</strong></p>
        </div>"""

    content = f"""
<h2>Inbox inviti</h2>
<h3>In arrivo</h3>
<div class="stack">{''.join(map(row_in, incoming)) or '<p>Nessun invito in arrivo.</p>'}</div>
<h3>Inviati</h3>
<div class="stack">{''.join(map(row_out, outgoing)) or '<p>Nessun invito inviato.</p>'}</div>"""
    return layout(me, content, "Inbox — Team Orthonext")

@app.get("/user/{user_id}", response_class=HTMLResponse)
def view_user(user_id: int, request: Request):
    with Session(engine) as s:
        user = s.get(User, user_id)
        me = s.get(User, get_current_user_id(request)) if get_current_user_id(request) else None
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    content = f"""
<h2>{user.full_name}</h2>
<div class="card">
  <p><strong>Specialità:</strong> {user.specialty}</p>
  <p><strong>Sottospecialità:</strong> {user.sub_specialties}</p>
  <p><strong>Regione:</strong> {user.region} — {user.city}</p>
  <p><strong>Ospedali:</strong> {user.hospital_affiliations}</p>
  <p><strong>Lingue:</strong> {user.languages}</p>
  <p><strong>Disponibilità:</strong> {user.availability}</p>
  <p><strong>Bio:</strong> {user.bio}</p>
</div>"""
    return layout(me, content, f"{user.full_name} — Team Orthonext")
