import os
import re
import sqlite3
import secrets
from datetime import datetime
from functools import wraps

from flask import (
Flask,
request,
redirect,
url_for,
session,
abort,
flash,
render_template_string,
send_from_directory,
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

=========================================================
JFGK STUDIO — PYTHON DEVELOPMENT WEBSITE
=========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
"JFGK_SECRET_KEY",
"jfgk-studio-change-this-secret-key"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "site.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

=========================================================
CONTACTS
=========================================================

CONTACTS = {
"phone": "+79856670184",
"telegram": "@Jeyke_4",
"email": "Dunaevilya240710@gmail.com",
}

=========================================================
DATABASE
=========================================================

def get_db():
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
return db

def init_db():
db = get_db()

db.executescript("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE NOT NULL,
password TEXT NOT NULL,
phone TEXT DEFAULT '',
email TEXT DEFAULT '',
birthdate TEXT DEFAULT '',
avatar TEXT DEFAULT '',
bio TEXT DEFAULT '',
is_provider INTEGER DEFAULT 0,
show_phone INTEGER DEFAULT 1,
show_email INTEGER DEFAULT 1,
show_birthdate INTEGER DEFAULT 0,
created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
id INTEGER PRIMARY KEY AUTOINCREMENT,
client_id INTEGER NOT NULL,
provider_id INTEGER NOT NULL,
title TEXT NOT NULL,
description TEXT NOT NULL,
budget TEXT DEFAULT '',
status TEXT DEFAULT 'new',
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL,
FOREIGN KEY(client_id) REFERENCES users(id),
FOREIGN KEY(provider_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS messages (
id INTEGER PRIMARY KEY AUTOINCREMENT,
order_id INTEGER NOT NULL,
sender_id INTEGER NOT NULL,
text TEXT NOT NULL,
created_at TEXT NOT NULL,
FOREIGN KEY(order_id) REFERENCES orders(id),
FOREIGN KEY(sender_id) REFERENCES users(id)
);
""")

db.commit()
db.close()

init_db()

=========================================================
HELPERS
=========================================================

def now():
return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def current_user():
user_id = session.get("user_id")

if not user_id:
return None

db = get_db()
user = db.execute(
"SELECT * FROM users WHERE id = ?",
(user_id,)
).fetchone()
db.close()

return user

def login_required(view):
@wraps(view)
def wrapped(*args, **kwargs):
if not current_user():
flash("Сначала войдите в аккаунт.", "error")
return redirect(url_for("login"))
return view(*args, **kwargs)

return wrapped

def provider_required(view):
@wraps(view)
def wrapped(*args, **kwargs):
user = current_user()

if not user:
flash("Сначала войдите в аккаунт.", "error")
return redirect(url_for("login"))

if not user["is_provider"]:
flash("Эта функция доступна исполнителю.", "error")
return redirect(url_for("dashboard"))

return view(*args, **kwargs)

return wrapped

=========================================================
CSRF
=========================================================

def csrf_token():
if "csrf" not in session:
session["csrf"] = secrets.token_hex(32)

return session["csrf"]

def check_csrf():
token = request.form.get("csrf", "")

if not token or token != session.get("csrf"):
abort(400)

=========================================================
HTML BASE
=========================================================

BASE_HTML = """
<!doctype html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta
name="viewport"
content="width=device-width, initial-scale=1.0"
>

<title>{{ title }} — JFGK Studio</title>

<meta
name="description"
content="{{ description }}"
>

<style>
* {
box-sizing: border-box;
}

html {
scroll-behavior: smooth;
}

body {
margin: 0;
background: #0b1020;
color: #f5f7ff;
font-family:
-apple-system,
BlinkMacSystemFont,
"Segoe UI",
Roboto,
Arial,
sans-serif;
}

a {
color: inherit;
text-decoration: none;
}

.container {
width: min(1120px, calc(100% - 30px));
margin: auto;
}

header {
position: sticky;
top: 0;
z-index: 100;
background: rgba(11, 16, 32, .94);
backdrop-filter: blur(14px);
border-bottom: 1px solid #202944;
}

.nav {
min-height: 70px;
display: flex;
align-items: center;
justify-content: space-between;
gap: 20px;
}

.logo {
font-weight: 900;
font-size: 20px;
letter-spacing: -.5px;
}

.logo span {
color: #6ea8ff;
}

nav {
display: flex;
flex-wrap: wrap;
gap: 8px;
align-items: center;
}

nav a {
color: #b9c3dd;
padding: 9px 11px;
border-radius: 10px;
}

nav a:hover {
background: #171f37;
color: white;
}

main {
min-height: calc(100vh - 220px);
padding: 35px 0 60px;
}

footer {
border-top: 1px solid #202944;
background: #080c18;
padding: 35px 0;
color: #9ca8c5;
}

footer h3 {
margin-top: 0;
color: white;
}

.hero {
padding: 65px 0;
}

.hero h1 {
max-width: 850px;
margin: 0 0 20px;
font-size: clamp(38px, 8vw, 74px);
line-height: .98;
letter-spacing: -3px;
}

.hero p {
max-width: 720px;
font-size: 19px;
line-height: 1.7;
color: #aeb9d4;
}

.badge {
display: inline-block;
padding: 7px 11px;
border-radius: 999px;
background: #172440;
color: #8db8ff;
font-size: 13px;
font-weight: 700;
margin-bottom: 16px;
}

.buttons {
display: flex;
flex-wrap: wrap;
gap: 10px;
margin-top: 25px;
}

.btn {
display: inline-block;
border: 0;
cursor: pointer;
padding: 12px 17px;
border-radius: 12px;
background: #4f8cff;
color: white;
font-weight: 800;
font-size: 15px;
}

.btn:hover {
opacity: .9;
}

.btn.secondary {
background: #1a233d;
color: #dce5ff;
}

.btn.danger {
background: #a43d4c;
}

.btn.success {
background: #267653;
}

.grid {
display: grid;
grid-template-columns: repeat(3, 1fr);
gap: 16px;
}

.grid-2 {
display: grid;
grid-template-columns: repeat(2, 1fr);
gap: 16px;
}

.card {
background: #11182b;
border: 1px solid #202944;
border-radius: 18px;
padding: 22px;
}

.card h2,
.card h3 {
margin-top: 0;
}

.muted {
color: #94a0bd;
}

.small {
font-size: 13px;
}

.price {
font-size: 28px;
font-weight: 900;
margin: 15px 0;
}

.form {
max-width: 650px;
}

label {
display: block;
margin: 15px 0 7px;
color: #dce4f8;
font-weight: 700;
}

input,
textarea,
select {
width: 100%;
border: 1px solid #2a3554;
background: #0b1122;
color: white;
border-radius: 11px;
padding: 12px 13px;
font-size: 15px;
outline: none;
}

textarea {
min-height: 130px;
resize: vertical;
}

input:focus,
textarea:focus,
select:focus {
border-color: #568fff;
}

.check {
display: flex;
gap: 9px;
align-items: center;
margin: 12px 0;
}

.check input {
width: auto;
}

.alert {
padding: 13px 15px;
border-radius: 12px;
background: #1b2948;
border: 1px solid #304b7a;
margin-bottom: 15px;
}

.alert.error {
background: #351b26;
border-color: #703746;
}

.alert.success {
background: #163427;
border-color: #286248;
}

.avatar {
width: 76px;
height: 76px;
object-fit: cover;
border-radius: 50%;
background: #1c2742;
border: 2px solid #304064;
}

.profile-head {
display: flex;
align-items: center;
gap: 17px;
margin-bottom: 25px;
}

.profile-head h1 {
margin: 0;
}

.status {
display: inline-block;
padding: 5px 9px;
border-radius: 999px;
background: #1a2948;
color: #a9c7ff;
font-size: 12px;
font-weight: 800;
}

.chat {
display: flex;
flex-direction: column;
gap: 10px;
margin: 20px 0;
}

.message {
max-width: 80%;
padding: 11px 14px;
border-radius: 14px;
background: #17213a;
}

.message.mine {
align-self: flex-end;
background: #2859a8;
}

.message .meta {
font-size: 11px;
color: #aab5ce;
margin-bottom: 4px;
}

table {
width: 100%;
border-collapse: collapse;
}

th,
td {
padding: 11px;
border-bottom: 1px solid #25304b;
text-align: left;
}

.contact {
display: grid;
gap: 8px;
}

.contact a {
color: #8fb7ff;
}

.empty {
padding: 30px;
text-align: center;
border: 1px dashed #35415e;
border-radius: 15px;
color: #909db9;
}

@media (max-width: 800px) {
.grid,
.grid-2 {
grid-template-columns: 1fr;
}

.nav {
padding: 10px 0;
align-items: flex-start;
flex-direction: column;
}

nav {
width: 100%;
}

nav a {
padding: 7px 8px;
}

.hero {
padding: 35px 0;
}

.hero h1 {
letter-spacing: -1.5px;
}

.message {
max-width: 92%;
}
}
</style>
</head>

<body>

<header>
<div class="container nav">

<a class="logo" href="{{ url_for('home') }}">
JFGK <span>Studio</span>
</a>

<nav>
<a href="{{ url_for('home') }}">Главная</a>
<a href="{{ url_for('services') }}">Услуги</a>

{% if user %}
<a href="{{ url_for('dashboard') }}">Заказы</a>
<a href="{{ url_for('profile') }}">Профиль</a>
<a href="{{ url_for('logout') }}">Выйти</a>
{% else %}
<a href="{{ url_for('login') }}">Войти</a>
<a href="{{ url_for('register') }}">Регистрация</a>
{% endif %}
</nav>

</div>
</header>

<main>
<div class="container">

{% with messages = get_flashed_messages(with_categories=true) %}
{% for category, message in messages %}
<div class="alert {{ category }}">
{{ message }}
</div>
{% endfor %}
{% endwith %}

{{ page|safe }}

</div>
</main>

<footer>
<div class="container">

<h3>JFGK Studio</h3>

<p>
Разработка приложений и автоматизации на Python.
</p>

<p>
Сайт создан <strong>JFGK Studio</strong>.
</p>

<div class="contact">

<div>
Телефон:
<a href="tel:{{ contacts.phone }}">
{{ contacts.phone }}
</a>
</div>

<div>
Telegram:
<a href="https://t.me/{{ contacts.telegram.replace('@', '') }}"
target="_blank">
{{ contacts.telegram }}
</a>
</div>

<div>
Email:
<a href="mailto:{{ contacts.email }}">
{{ contacts.email }}
</a>
</div>

</div>

<p class="small">
© {{ current_year }} JFGK Studio
</p>

</div>
</footer>

</body>
</html>
"""

=========================================================
PAGE RENDERER
=========================================================
ВАЖНО:
Сначала отдельно рендерим page,
а уже потом вставляем готовый HTML в BASE_HTML.
Именно это исправляет проблему:
/{{ url_for('home') }}
и ошибку регистрации 400.
=========================================================

def render_page(title, page, description="JFGK Studio — Python Development", **kwargs):

user = current_user()

context = {
"title": title,
"description": description,
"user": user,
"contacts": CONTACTS,
"csrf": csrf_token(),
"current_year": datetime.now().year,
}

context.update(kwargs)

rendered_page = render_template_string(
page,
**context
)

return render_template_string(
BASE_HTML,
title=title,
description=description,
page=rendered_page,
user=user,
contacts=CONTACTS,
csrf=context["csrf"],
current_year=datetime.now().year
)

=========================================================
HOME
=========================================================

@app.route("/")
def home():

page = """
<section class="hero">

<div class="badge">
JFGK Studio · Python Development
</div>

<h1>
Разработка приложений на Python
</h1>

<p>
Здесь можно заказать разработку Python-приложения,
автоматизацию, Telegram-бота, парсер или другой
программный проект.
</p>

<div class="buttons">
<a class="btn" href="{{ url_for('services') }}">
Посмотреть услуги
</a>

{% if user %}
<a class="btn secondary"
href="{{ url_for('order_new') }}">
Создать заказ
</a>
{% else %}
<a class="btn secondary"
href="{{ url_for('register') }}">
Создать аккаунт
</a>
{% endif %}
</div>

</section>

<section>

<div class="grid">

<div class="card">
<h3>Python</h3>
<p class="muted">
Создание приложений, скриптов и автоматизации
на Python.
</p>
</div>

<div class="card">
<h3>Боты</h3>
<p class="muted">
Telegram-боты и другие автоматизированные
решения.
</p>
</div>

<div class="card">
<h3>Индивидуальные проекты</h3>
<p class="muted">
Можно описать свою задачу и обсудить её
напрямую через заказ.
</p>
</div>

</div>

</section>

<section style="margin-top:25px">

<div class="card">

<h2>Как это работает</h2>

<ol class="muted">
<li>Создайте аккаунт.</li>
<li>Опишите необходимое приложение.</li>
<li>Укажите бюджет и детали.</li>
<li>Создайте заказ.</li>
<li>Общайтесь с исполнителем в чате заказа.</li>
</ol>

</div>

</section>
"""

return render_page(
"Главная",
page,
"JFGK Studio — разработка приложений и автоматизации на Python."
)

=========================================================
SERVICES
=========================================================

@app.route("/services/python-development")
def services():

page = """
<div class="badge">Услуги</div>

<h1>Python-разработка</h1>

<p class="muted">
Выберите направление или создайте индивидуальный заказ.
</p>

<div class="grid">

<div class="card">
<h2>Python-приложение</h2>

<p class="muted">
Разработка небольших программ и приложений
под конкретную задачу.
</p>

<div class="price">
По договорённости
</div>

<a class="btn"
href="{{ url_for('order_new') }}">
Заказать
</a>
</div>

<div class="card">
<h2>Telegram-бот</h2>

<p class="muted">
Боты для автоматизации общения, обработки
заявок и других задач.
</p>

<div class="price">
По договорённости
</div>

<a class="btn"
href="{{ url_for('order_new') }}">
Заказать
</a>
</div>

<div class="card">
<h2>Автоматизация</h2>

<p class="muted">
Скрипты, обработка данных и автоматизация
повторяющихся действий.
</p>

<div class="price">
По договорённости
</div>

<a class="btn"
href="{{ url_for('order_new') }}">
Заказать
</a>
</div>

<div class="card">
<h2>Индивидуальный проект</h2>

<p class="muted">
Если вашей задачи нет в списке — просто
опишите её.
</p>

<div class="price">
Обсуждение
</div>

<a class="btn"
href="{{ url_for('order_new') }}">
Описать задачу
</a>
</div>

</div>
"""

return render_page(
"Услуги",
page,
"Услуги JFGK Studio по разработке приложений на Python."
)

=========================================================
REGISTER
=========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

if current_user():
return redirect(url_for("dashboard"))

if request.method == "POST":

check_csrf()

username = request.form.get("username", "").strip()
password = request.form.get("password", "")
phone = request.form.get("phone", "").strip()
email = request.form.get("email", "").strip()
birthdate = request.form.get("birthdate", "").strip()

if len(username) < 3:
flash(
"Никнейм должен содержать минимум 3 символа.",
"error"
)
return redirect(url_for("register"))

if len(password) < 6:
flash(
"Пароль должен содержать минимум 6 символов.",
"error"
)
return redirect(url_for("register"))

if not re.match(r"^[A-Za-zА-Яа-яЁё0-9_.-]+$", username):
flash(
"В никнейме разрешены буквы, цифры, _, . и -.",
"error"
)
return redirect(url_for("register"))

db = get_db()

exists = db.execute(
"SELECT id FROM users WHERE username = ?",
(username,)
).fetchone()

if exists:
db.close()

flash(
"Такой никнейм уже занят.",
"error"
)

return redirect(url_for("register"))

count = db.execute(
"SELECT COUNT(*) AS c FROM users"
).fetchone()["c"]

# Первый зарегистрированный пользователь
# автоматически становится исполнителем.
is_provider = 1 if count == 0 else 0

db.execute(
"""
INSERT INTO users (
username,
password,
phone,
email,
birthdate,
is_provider,
created_at
)
VALUES (?, ?, ?, ?, ?, ?, ?)
""",
(
username,
generate_password_hash(password),
phone,
email,
birthdate,
is_provider,
now()
)
)

db.commit()

user = db.execute(
"SELECT id FROM users WHERE username = ?",
(username,)
).fetchone()

db.close()

session["user_id"] = user["id"]

if is_provider:
flash(
"Аккаунт создан. Вы зарегистрированы как исполнитель.",
"success"
)
else:
flash(
"Аккаунт успешно создан.",
"success"
)

return redirect(url_for("dashboard"))

page = """
<div class="card form">

<h1>Регистрация</h1>

<p class="muted">
Создайте аккаунт на JFGK Studio.
</p>

<form method="post">

<input
type="hidden"
name="csrf"
value="{{ csrf }}"
>

<label>Никнейм</label>

<input
type="text"
name="username"
required
minlength="3"
placeholder="Например: Jeyke"
>

<label>Пароль</label>

<input
type="password"
name="password"
required
minlength="6"
placeholder="Минимум 6 символов"
>

<label>Телефон</label>

<input
type="tel"
name="phone"
placeholder="+7..."
>

<label>Email</label>

<input
type="email"
name="email"
placeholder="example@mail.com"
>

<label>Дата рождения</label>

<input
type="date"
name="birthdate"
>

<div class="buttons">

<button class="btn" type="submit">
Зарегистрироваться
</button>

<a class="btn secondary"
href="{{ url_for('login') }}">
Уже есть аккаунт
</a>

</div>

</form>

</div>
"""

return render_page(
"Регистрация",
page,
"Регистрация на JFGK Studio."
)

=========================================================
LOGIN
=========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

if current_user():
return redirect(url_for("dashboard"))

if request.method == "POST":

check_csrf()

username = request.form.get("username", "").strip()
password = request.form.get("password", "")

db = get_db()

user = db.execute(
"SELECT * FROM users WHERE username = ?",
(username,)
).fetchone()

db.close()

if not user or not check_password_hash(
user["password"],
password
):
flash(
"Неверный никнейм или пароль.",
"error"
)
return redirect(url_for("login"))

session["user_id"] = user["id"]

flash(
"Вы успешно вошли.",
"success"
)

return redirect(url_for("dashboard"))

page = """
<div class="card form">

<h1>Вход</h1>

<form method="post">

<input
type="hidden"
name="csrf"
value="{{ csrf }}"
>

<label>Никнейм</label>

<input
type="text"
name="username"
required
>

<label>Пароль</label>

<input
type="password"
name="password"
required
>

<div class="buttons">

<button class="btn" type="submit">
Войти
</button>

<a class="btn secondary"
href="{{ url_for('register') }}">
Регистрация
</a>

</div>

</form>

</div>
"""

return render_page(
"Вход",
page,
"Вход в аккаунт JFGK Studio."
)

=========================================================
LOGOUT
=========================================================

@app.route("/logout")
def logout():

session.pop("user_id", None)

flash(
"Вы вышли из аккаунта.",
"success"
)

return redirect(url_for("home"))

=========================================================
DASHBOARD
=========================================================

@app.route("/dashboard")
@login_required
def dashboard():

user = current_user()

db = get_db()

orders = db.execute(
"""
SELECT
orders.*,
client.username AS client_username,
provider.username AS provider_username
FROM orders
LEFT JOIN users client
ON client.id = orders.client_id
LEFT JOIN users provider
ON provider.id = orders.provider_id
WHERE orders.client_id = ?
OR orders.provider_id = ?
ORDER BY orders.updated_at DESC
""",
(user["id"], user["id"])
).fetchall()

db.close()

page = """
<div class="profile-head">

{% if user.avatar %}
<img
class="avatar"
src="{{ url_for('uploaded_file', filename=user.avatar) }}"
>
{% else %}
<div class="avatar"></div>
{% endif %}

<div>
<h1>Привет, {{ user.username }}!</h1>

{% if user.is_provider %}
<span class="status">
Исполнитель
</span>
{% else %}
<span class="status">
Заказчик
</span>
{% endif %}
</div>

</div>

<div class="buttons">

<a class="btn"
href="{{ url_for('order_new') }}">
+ Новый заказ
</a>

<a class="btn secondary"
href="{{ url_for('profile') }}">
Настроить профиль
</a>

</div>

<div style="margin-top:30px">

<h2>Мои заказы</h2>

{% if orders %}

<div class="grid">

{% for order in orders %}

<div class="card">

<span class="status">
{{ order.status }}
</span>

<h3>
{{ order.title }}
</h3>

<p class="muted">
{{ order.description[:180] }}
{% if order.description|length > 180 %}
...
{% endif %}
</p>

<p class="small muted">
Заказчик:
{{ order.client_username }}
</p>

<p class="small muted">
Исполнитель:
{{ order.provider_username }}
</p>

<a class="btn"
href="{{ url_for('order_view', order_id=order.id) }}">
Открыть
</a>

</div>

{% endfor %}

</div>

{% else %}

<div class="empty">
У вас пока нет заказов.
</div>

{% endif %}

</div>
"""

return render_page(
"Мои заказы",
page,
"Личный кабинет JFGK Studio.",
orders=orders
)

=========================================================
PROFILE
=========================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

user = current_user()

if request.method == "POST":

check_csrf()

username = request.form.get("username", "").strip()
phone = request.form.get("phone", "").strip()
email = request.form.get("email", "").strip()
birthdate = request.form.get("birthdate", "").strip()
bio = request.form.get("bio", "").strip()

show_phone = 1 if request.form.get("show_phone") else 0
show_email = 1 if request.form.get("show_email") else 0
show_birthdate = 1 if request.form.get("show_birthdate") else 0

if len(username) < 3:
flash(
"Никнейм слишком короткий.",
"error"
)
return redirect(url_for("profile"))

db = get_db()

duplicate = db.execute(
"""
SELECT id
FROM users
WHERE username = ?
AND id != ?
""",
(username, user["id"])
).fetchone()

if duplicate:
db.close()

flash(
"Этот никнейм уже занят.",
"error"
)

return redirect(url_for("profile"))

avatar_name = user["avatar"]

file = request.files.get("avatar")

if file and file.filename:

filename = secure_filename(file.filename)

allowed = {
".jpg",
".jpeg",
".png",
".gif",
".webp"
}

ext = os.path.splitext(filename)[1].lower()

if ext not in allowed:
db.close()

flash(
"Разрешены JPG, PNG, GIF и WEBP.",
"error"
)

return redirect(url_for("profile"))

new_name = (
secrets.token_hex(12)
+ ext
)

file.save(
os.path.join(
UPLOAD_DIR,
new_name
)
)

avatar_name = new_name

db.execute(
"""
UPDATE users
SET
username = ?,
phone = ?,
email = ?,
birthdate = ?,
bio = ?,
avatar = ?,
show_phone = ?,
show_email = ?,
show_birthdate = ?
WHERE id = ?
""",
(
username,
phone,
email,
birthdate,
bio,
avatar_name,
show_phone,
show_email,
show_birthdate,
user["id"]
)
)

db.commit()
db.close()

flash(
"Профиль сохранён.",
"success"
)

return redirect(url_for("profile"))

page = """
<div class="card form">

<h1>Мой профиль</h1>

{% if user.avatar %}

<img
class="avatar"
src="{{ url_for('uploaded_file', filename=user.avatar) }}"
>

{% endif %}

<form method="post"
enctype="multipart/form-data">

<input
type="hidden"
name="csrf"
value="{{ csrf }}"
>

<label>Аватар</label>

<input
type="file"
name="avatar"
accept="image/*"
>

<label>Никнейм</label>

<input
type="text"
name="username"
value="{{ user.username }}"
required
>

<label>Телефон</label>

<input
type="tel"
name="phone"
value="{{ user.phone }}"
>

<label>Email</label>

<input
type="email"
name="email"
value="{{ user.email }}"
>

<label>Дата рождения</label>

<input
type="date"
name="birthdate"
value="{{ user.birthdate }}"
>

<label>О себе</label>

<textarea name="bio"
placeholder="Расскажите немного о себе...">{{ user.bio }}</textarea>

<h3>Приватность</h3>

<label class="check">
<input
type="checkbox"
name="show_phone"
{% if user.show_phone %}checked{% endif %}
>
Показывать телефон
</label>

<label class="check">
<input
type="checkbox"
name="show_email"
{% if user.show_email %}checked{% endif %}
>
Показывать email
</label>

<label class="check">
<input
type="checkbox"
name="show_birthdate"
{% if user.show_birthdate %}checked{% endif %}
>
Показывать дату рождения
</label>

<div class="buttons">

<button class="btn" type="submit">
Сохранить
</button>

<a class="btn secondary"
href="{{ url_for('public_profile', username=user.username) }}">
Открыть публичный профиль
</a>

</div>

</form>

</div>
"""

return render_page(
"Профиль",
page,
"Профиль пользователя JFGK Studio."
)

=========================================================
PUBLIC PROFILE
=========================================================

@app.route("/u/<username>")
def public_profile(username):

db = get_db()

user = db.execute(
"SELECT * FROM users WHERE username = ?",
(username,)
).fetchone()

db.close()

if not user:
abort(404)

page = """
<div class="card">

<div class="profile-head">

{% if profile.avatar %}

<img
class="avatar"
src="{{ url_for('uploaded_file', filename=profile.avatar) }}"
>

{% else %}

<div class="avatar"></div>

{% endif %}

<div>

<h1>{{ profile.username }}</h1>

{% if profile.is_provider %}
<span class="status">
Исполнитель
</span>
{% endif %}

</div>

</div>

{% if profile.bio %}

<h3>О себе</h3>

<p class="muted">
{{ profile.bio }}
</p>

{% endif %}

<div class="contact">

{% if profile.show_phone and profile.phone %}

<div>
Телефон:
<a href="tel:{{ profile.phone }}">
{{ profile.phone }}
</a>
</div>

{% endif %}

{% if profile.show_email and profile.email %}

<div>
Email:
<a href="mailto:{{ profile.email }}">
{{ profile.email }}
</a>
</div>

{% endif %}

{% if profile.show_birthdate and profile.birthdate %}

<div>
Дата рождения:
{{ profile.birthdate }}
</div>

{% endif %}

</div>

{% if profile.is_provider %}

<div class="buttons">

<a class="btn"
href="{{ url_for('order_new') }}">
Создать заказ
</a>

</div>

{% endif %}

</div>
"""

return render_page(
profile["username"],
page,
f"Профиль {profile['username']} — JFGK Studio.",
profile=user
)

=========================================================
CREATE ORDER
=========================================================

@app.route("/order/new", methods=["GET", "POST"])
@login_required
def order_new():

user = current_user()

if request.method == "POST":

check_csrf()

title = request.form.get("title", "").strip()
description = request.form.get("description", "").strip()
budget = request.form.get("budget", "").strip()

if len(title) < 3:
flash(
"Название заказа слишком короткое.",
"error"
)
return redirect(url_for("order_new"))

if len(description) < 10:
flash(
"Опишите задачу подробнее.",
"error"
)
return redirect(url_for("order_new"))

db = get_db()

provider = db.execute(
"""
SELECT *
FROM users
WHERE is_provider = 1
ORDER BY id ASC
LIMIT 1
"""
).fetchone()

if not provider:
db.close()

flash(
"Сейчас нет доступного исполнителя.",
"error"
)

return redirect(url_for("dashboard"))

db.execute(
"""
INSERT INTO orders (
client_id,
provider_id,
title,
description,
budget,
status,
created_at,
updated_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""",
(
user["id"],
provider["id"],
title,
description,
budget,
"new",
now(),
now()
)
)

order_id = db.execute(
"SELECT last_insert_rowid()"
).fetchone()[0]

db.commit()
db.close()

flash(
"Заказ создан.",
"success"
)

return redirect(
url_for(
"order_view",
order_id=order_id
)
)

page = """
<div class="card form">

<h1>Новый заказ</h1>

<p class="muted">
Опишите, какое Python-приложение вам необходимо.
</p>

<form method="post">

<input
type="hidden"
name="csrf"
value="{{ csrf }}"
>

<label>Название</label>

<input
type="text"
name="title"
required
placeholder="Например: Telegram-бот"
>

<label>Описание задачи</label>

<textarea
name="description"
required
placeholder="Подробно опишите, что должно делать приложение..."
></textarea>

<label>Бюджет</label>

<input
type="text"
name="budget"
placeholder="Например: 5000 ₽"
>

<div class="buttons">

<button class="btn" type="submit">
Создать заказ
</button>

<a class="btn secondary"
href="{{ url_for('dashboard') }}">
Отмена
</a>

</div>

</form>

</div>
"""

return render_page(
"Новый заказ",
page,
"Создание заказа на разработку Python-приложения."
)

=========================================================
ORDER VIEW
=========================================================

@app.route("/order/<int:order_id>", methods=["GET", "POST"])
@login_required
def order_view(order_id):

user = current_user()

db = get_db()

order = db.execute(
"""
SELECT
orders.*,
client.username AS client_username,
provider.username AS provider_username
FROM orders
LEFT JOIN users client
ON client.id = orders.client_id
LEFT JOIN users provider
ON provider.id = orders.provider_id
WHERE orders.id = ?
""",
(order_id,)
).fetchone()

if not order:
db.close()
abort(404)

if user["id"] not in (
order["client_id"],
order["provider_id"]
):
db.close()
abort(403)

if request.method == "POST":

check_csrf()

action = request.form.get("action")

if action == "message":

text = request.form.get("text", "").strip()

if text:

db.execute(
"""
INSERT INTO messages (
order_id,
sender_id,
text,
created_at
)
VALUES (?, ?, ?, ?)
""",
(
order_id,
user["id"],
text,
now()
)
)

db.execute(
"""
UPDATE orders
SET updated_at = ?
WHERE id = ?
""",
(
now(),
order_id
)
)

db.commit()

elif action == "status":

new_status = request.form.get("status")

allowed_statuses = {
"new",
"in_progress",
"completed",
"cancelled"
}

if new_status in allowed_statuses:

db.execute(
"""
UPDATE orders
SET
status = ?,
updated_at = ?
WHERE id = ?
""",
(
new_status,
now(),
order_id
)
)

db.commit()

db.close()

return redirect(
url_for(
"order_view",
order_id=order_id
)
)

messages = db.execute(
"""
SELECT
messages.*,
users.username
FROM messages
JOIN users
ON users.id = messages.sender_id
WHERE messages.order_id = ?
ORDER BY messages.id ASC
""",
(order_id,)
).fetchall()

db.close()

page = """
<div class="card">

<div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">

<div>
<span class="status">
{{ order.status }}
</span>

<h1>
{{ order.title }}
</h1>
</div>

<div>
<a class="btn secondary"
href="{{ url_for('dashboard') }}">
← К заказам
</a>
</div>

</div>

<h3>Описание</h3>

<p class="muted">
{{ order.description }}
</p>

{% if order.budget %}

<p>
<strong>Бюджет:</strong>
{{ order.budget }}
</p>

{% endif %}

<div class="grid-2">

<div>
<p class="small muted">
Заказчик
</p>

<a href="{{ url_for(
'public_profile',
username=order.client_username
) }}">
{{ order.client_username }}
</a>
</div>

<div>
<p class="small muted">
Исполнитель
</p>

<a href="{{ url_for(
'public_profile',
username=order.provider_username
) }}">
{{ order.provider_username }}
</a>
</div>

</div>

</div>

<div class="card" style="margin-top:20px">

<h2>Статус заказа</h2>

<form method="post">

<input
type="hidden"
name="csrf"
value="{{ csrf }}"
>

<input
type="hidden"
name="action"
value="status"
>

<select name="status">

<option
value="new"
{% if order.status == "new" %}selected{% endif %}
>
Новый
</option>

<option
value="in_progress"
{% if order.status == "in_progress" %}selected{% endif %}
>
В работе
</option>

<option
value="completed"
{% if order.status == "completed" %}selected{% endif %}
>
Выполнен
</option>

<option
value="cancelled"
{% if order.status == "cancelled" %}selected{% endif %}
>
Отменён
</option>

</select>

<div class="buttons">

<button class="btn" type="submit">
Изменить статус
</button>

</div>

</form>

</div>

<div class="card" style="margin-top:20px">

<h2>Чат по заказу</h2>

{% if messages %}

<div class="chat">

{% for message in messages %}

<div class="message
{% if message.sender_id == user.id %}
mine
{% endif %}
">

<div class="meta">
{{ message.username }}
·
{{ message.created_at }}
</div>

<div>
{{ message.text }}
</div>

</div>

{% endfor %}

</div>

{% else %}

<div class="empty">
Пока сообщений нет.
</div>

{% endif %}

<form method="post">

<input
type="hidden"
name="csrf"
value="{{ csrf }}"
>

<input
type="hidden"
name="action"
value="message"
>

<label>Сообщение</label>

<textarea
name="text"
required
placeholder="Напишите сообщение..."
></textarea>

<div class="buttons">

<button class="btn" type="submit">
Отправить
</button>

</div>

</form>

</div>
"""

return render_page(
f"Заказ #{order_id}",
page,
f"Заказ #{order_id} — JFGK Studio.",
order=order,
messages=messages
)

=========================================================
UPLOADS
=========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
return send_from_directory(
UPLOAD_DIR,
filename
)

=========================================================
ROBOTS.TXT
=========================================================

@app.route("/robots.txt")
def robots():

return (
"User-agent: *\n"
"Allow: /\n"
"Sitemap: "
+ request.url_root.rstrip("/")
+ "/sitemap.xml\n"
), 200, {
"Content-Type": "text/plain; charset=utf-8"
}

=========================================================
SITEMAP.XML
=========================================================

@app.route("/sitemap.xml")
def sitemap():

base = request.url_root.rstrip("/")

urls = [
base + "/",
base + "/services/python-development",
base + "/login",
base + "/register",
 ]

xml = '<?xml version="1.0" encoding="UTF-8"?>'
xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

for item in urls:
xml += "<url>"
xml += f"<loc>{item}</loc>"
xml += "</url>"

xml += "</urlset>"

return xml, 200, {
"Content-Type": "application/xml; charset=utf-8"
}

=========================================================
ERROR PAGES
=========================================================

@app.errorhandler(400)
def bad_request(error):

page = """
<div class="card">

<h1>400</h1>

<h2>Неверный запрос</h2>

<p class="muted">
Возможно, страница была открыта слишком давно.
Попробуйте обновить страницу.
</p>

<a class="btn"
href="{{ url_for('home') }}">
На главную
</a>

</div>
"""

return render_page(
"Ошибка 400",
page
), 400

@app.errorhandler(403)
def forbidden(error):

page = """
<div class="card">

<h1>403</h1>

<h2>Доступ запрещён</h2>

<a class="btn"
href="{{ url_for('home') }}">
На главную
</a>

</div>
"""

return render_page(
"Ошибка 403",
page
), 403

@app.errorhandler(404)
def not_found(error):

page = """
<div class="card">

<h1>404</h1>

<h2>Страница не найдена</h2>

<p class="muted">
Такой страницы не существует.
</p>

<a class="btn"
href="{{ url_for('home') }}">
На главную
</a>

</div>
"""

return render_page(
"Страница не найдена",
page
), 404

=========================================================
START
=========================================================

if __name__ == "__main__":

print()
print("=" * 55)
print("JFGK STUDIO")
print("Python Development Website")
print("=" * 55)
print()
print("САЙТ ЗАПУЩЕН")
print()
print("Открой в браузере:")
print("http://127.0.0.1:5000")
print()
print("Регистрация:")
print("http://127.0.0.1:5000/register")
print()
print("Для остановки нажми CTRL+C")
print("=" * 55)
print()

app.run(
host="0.0.0.0",
port=5000,
debug=False
)