from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import os, time, sqlite3, jwt, secrets

# ---------------- CONFIG ----------------
JWT_SECRET = "lakecityrecordingstudio"   # change before production
JWT_ALGO = "HS256"
ADMIN_USER = "JAMES"
ADMIN_PASS = "001JAMES"   # demo only (not secure!)

BASE_DIR = os.path.dirname(__file__)
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

# Serve static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, content TEXT, image_url TEXT, created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT, event_date TEXT, price TEXT, location TEXT, link TEXT, image_url TEXT, created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS programmes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, description TEXT, start_date TEXT, end_date TEXT, image_url TEXT, created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, price TEXT, currency TEXT, description TEXT, image_url TEXT, product_url TEXT, created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE, created_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT, client_email TEXT, item_type TEXT, item_id INTEGER, quantity INTEGER, created_at INTEGER
    );
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

# ---------------- UPLOAD ROUTES ----------------
@app.post("/admin/upload/programme")
def upload_programme(title: str, description: str, start_date: str, end_date: str,
                     file: UploadFile = File(...), user=Depends(verify_token_header)):
    filename = f"programme_{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO programmes (title, description, start_date, end_date, image_url, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, description, start_date, end_date, f"/static/uploads/{filename}", int(time.time())))
    conn.commit()
    conn.close()
    return {"message": "Programme uploaded", "image_url": f"/static/uploads/{filename}"}

@app.post("/admin/upload/product")
def upload_product(name: str, price: str, currency: str, description: str,
                   file: UploadFile = File(...), user=Depends(verify_token_header)):
    filename = f"product_{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO products (name, price, currency, description, image_url, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, price, currency, description, f"/static/uploads/{filename}", int(time.time())))
    conn.commit()
    conn.close()
    return {"message": "Product uploaded", "image_url": f"/static/uploads/{filename}"}

@app.post("/admin/upload/news")
def upload_news(title: str, content: str, file: UploadFile = File(...),
                user=Depends(verify_token_header)):
    filename = f"news_{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO news (title, content, image_url, created_at)
                   VALUES (?, ?, ?, ?)""",
                (title, content, f"/static/uploads/{filename}", int(time.time())))
    conn.commit()
    conn.close()
    return {"message": "News uploaded", "image_url": f"/static/uploads/{filename}"}

@app.post("/admin/upload/ticket")
def upload_ticket(event_name: str, event_date: str, price: str, location: str, link: str,
                  file: UploadFile = File(...), user=Depends(verify_token_header)):
    filename = f"ticket_{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO tickets (event_name, event_date, price, location, link, image_url, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_name, event_date, price, location, link, f"/static/uploads/{filename}", int(time.time())))
    conn.commit()
    conn.close()
    return {"message": "Ticket uploaded", "image_url": f"/static/uploads/{filename}"}

# ---------------- PUBLIC APIS ----------------
@app.get("/api/programmes")
def get_programmes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM programmes ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/products")
def get_products():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/news")
def get_news():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM news ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/tickets")
def get_tickets():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ---------------- NEWSLETTER ----------------
class SubscribeIn(BaseModel):
    email: str

@app.post("/api/subscribe")
def subscribe(sub: SubscribeIn):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO subscribers (email, created_at) VALUES (?, ?)",
                    (sub.email, int(time.time())))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(400, "Email already subscribed")
    conn.close()

    # also save in a txt file
    with open(os.path.join(BASE_DIR, "subscribers.txt"), "a") as f:
        f.write(f"{time.ctime()} | {sub.email}\n")

    return {"message": "Subscribed successfully"}

@app.get("/admin/subscribers")
def get_subscribers(user=Depends(verify_token_header)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscribers ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ---------------- ORDERS ----------------
class OrderIn(BaseModel):
    client_name: str
    client_email: str
    item_type: str   # "product" | "ticket" | "programme"
    item_id: int
    quantity: int

@app.post("/api/order")
def create_order(order: OrderIn):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""INSERT INTO orders (client_name, client_email, item_type, item_id, quantity, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (order.client_name, order.client_email, order.item_type,
                 order.item_id, order.quantity, int(time.time())))
    conn.commit()
    conn.close()

    # also save in a txt file
    log_line = f"{time.ctime()} | {order.client_name} | {order.client_email} | {order.item_type}:{order.item_id} | qty={order.quantity}\n"
    with open(os.path.join(BASE_DIR, "orders_log.txt"), "a") as f:
        f.write(log_line)

    return {"message": "Order saved successfully"}

# ---------------- ADMIN DELETE/EDIT ----------------
@app.delete("/admin/product/{product_id}")
def delete_product(product_id: int, user=Depends(verify_token_header)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Product deleted"}

class EditProgramme(BaseModel):
    title: str
    description: str
    start_date: str
    end_date: str

@app.put("/admin/programme/{programme_id}")
def edit_programme(programme_id: int, data: EditProgramme, user=Depends(verify_token_header)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""UPDATE programmes
                   SET title=?, description=?, start_date=?, end_date=?
                   WHERE id=?""",
                (data.title, data.description, data.start_date, data.end_date, programme_id))
    conn.commit()
    conn.close()
    return {"message": "Programme updated"}

# ---------------- MAIN ENTRY ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
