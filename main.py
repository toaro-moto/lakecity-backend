from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os, time, sqlite3, jwt, secrets

# ---------------- APP INIT ----------------
app = FastAPI(title="Lake City Studios API")

# ---------------- CONFIG ----------------
JWT_SECRET = "lakecityrecordingstudio"
JWT_ALGO = "HS256"
ADMIN_USER = "JAMES"
ADMIN_PASS = "001JAMES"

BASE_DIR = os.path.dirname(__file__)
ADMIN_DIR = os.path.join(BASE_DIR, "admin")

DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ADMIN_DIR, exist_ok=True)

# ---------------- MIDDLEWARE ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- STATIC ----------------
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ✅ keep the rest of your routes & DB code exactly the same...
