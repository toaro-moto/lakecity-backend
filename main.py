from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

import os
import pathlib
import secrets
import sqlite3
import base64
import requests
import jwt
import time
from datetime import datetime   # ✅ clean datetime import

# ---------------- CONFIG ----------------
JWT_SECRET = "lakecityrecordingstudio"  # change before production
JWT_ALGO = "HS256"
ADMIN_USER = "JAMES"
ADMIN_PASS = "001JAMES"  # demo only (not secure!)

BASE_DIR = os.path.dirname(__file__)

FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
ADMIN_DIR = os.path.join(BASE_DIR, "admin")

DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- APP INIT ----------------
app = FastAPI(title="Lake City Studios API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (images, css, js, uploads)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS news (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, created_at INTEGER);
    CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, event_name TEXT, event_date TEXT, price TEXT, location TEXT, link TEXT, created_at INTEGER);
    CREATE TABLE IF NOT EXISTS programmes (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, start_date TEXT, end_date TEXT, created_at INTEGER);
    CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, currency TEXT, description TEXT, image_url TEXT, product_url TEXT, created_at INTEGER);
    CREATE TABLE IF NOT EXISTS subscribers (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, created_at INTEGER);
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------- AUTH ----------------
class LoginIn(BaseModel):
    username: str
    password: str

@app.post("/auth/login")
def login(payload: LoginIn):
    if payload.username != ADMIN_USER or payload.password != ADMIN_PASS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = int(time.time())
    payload = {"sub": ADMIN_USER, "iat": now, "exp": now + 60*60*24}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return {"token": token, "user": {"username": ADMIN_USER}}

def verify_token_header(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return data

# ---------------- ADMIN HTML ROUTES ----------------
@app.get("/admin/login", response_class=FileResponse)
def serve_admin_login():
    file_path = os.path.join(ADMIN_DIR, "login.html")
    if not os.path.exists(file_path):
        raise HTTPException(404, f"Login page not found at {file_path}")
    return FileResponse(file_path)

@app.get("/admin/dashboard", response_class=FileResponse)
def serve_admin_dashboard(user=Depends(verify_token_header)):
    file_path = os.path.join(ADMIN_DIR, "dashboard.html")
    if not os.path.exists(file_path):
        raise HTTPException(404, f"Dashboard not found at {file_path}")
    return FileResponse(file_path)

# ---------------- FRONTEND HTML ROUTES ----------------
@app.get("/", response_class=FileResponse)
def serve_index():
    file_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(file_path):
        raise HTTPException(404, f"Index not found at {file_path}")
    return FileResponse(file_path)

@app.get("/{page_name}.html", response_class=FileResponse)
def serve_html_page(page_name: str):
    file_path = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(404, f"Page {page_name}.html not found")

# ---------------- MPESA INTEGRATION ----------------
MPESA_CONSUMER_KEY = "mj8H51HGdZ8SZptHiWDHGy3hJEVzew7A6YqfWaioy7xJsjgX"
MPESA_CONSUMER_SECRET = "YBE9x8dhVuNiY5ukBzTZgX3Cx1VEBANptMmjsAhMfRNPDj2oIceRrpuQ6B5x0fQr"
MPESA_SHORTCODE = "174379"  # sandbox test shortcode
MPESA_PASSKEY = "YOUR_PASSKEY"
MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"

def get_mpesa_token():
    resp = requests.get(
        f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
        auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET)
    )
    if resp.status_code != 200:
        raise HTTPException(500, "Failed to authenticate M-Pesa")
    return resp.json()["access_token"]

@app.post("/pay/mpesa")
def stk_push_payment(phone: str, amount: int):
    token = get_mpesa_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # ✅ clean datetime use
    password = base64.b64encode((MPESA_SHORTCODE + MPESA_PASSKEY + timestamp).encode()).decode()

    payload = {
        "BusinessShortCode": 600100,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://lakecitystudios.co.ke/api/mpesa/callback",
        "AccountReference": "0100011399414",
        "TransactionDesc": "Studio Booking Payment"
    }

    resp = requests.post(
        f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    return resp.json()

@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    print("✅ M-Pesa Callback:", data)
    # TODO: Save transaction into DB
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

# ---------------- MAIN ENTRY ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
