from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, HTMLResponse

app = FastAPI()

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><meta charset="utf-8">
<title>Team Orthonext - Hello</title>
<style>body{font-family:system-ui;margin:40px}code{background:#eee;padding:2px 6px;border-radius:6px}</style>
<h1>Team Orthonext</h1>
<p>Se vedi questa pagina, Render sta funzionando.</p>
<p>Prova <code>/health</code> → deve rispondere <strong>ok</strong>.</p>
"""
