import os
import secrets
import sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.environ.get("JFGK_SECRET_KEY") or secrets.token_hex(32)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "site.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            avatar TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Новая',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


BASE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #0f1115;
            color: #ffffff;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        .nav {
            background: #171a21;
            border-bottom: 1px solid #2b303a;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .logo {
            font-size: 24px;
            font-weight: 800;
        }

        .nav-links {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }

        .container {
            width: min(1100px, 92%);
            margin: 40px auto;
        }

        .hero {
            padding: 70px 30px;
            text-align: center;
            background: linear-gradient(135deg, #171a21, #222734);
            border-radius: 20px;
        }

        h1 {
            font-size: clamp(34px, 7vw, 64px);
            margin: 0 0 20px;
        }

        h2 {
            margin-top: 0;
        }

        .muted {
            color: #aeb5c2;
        }

        .btn {
            display: inline-block;
            border: 0;
            background: #ffffff;
            color: #111111;
            padding: 12px 20px;
            border-radius: 10px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }

        .btn.dark {
            background: #272c36;
            color: #ffffff;
        }

        .card {
            background: #171a21;
            border: 1px solid #2b303a;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }

        input,
        textarea,
        select {
            width: 100%;
            padding: 13px;
            margin: 7px 0 16px;
            border-radius: 9px;
            border: 1px solid #363c48;
            background: #101218;
            color: white;
        }

        textarea {
            min-height: 140px;
            resize: vertical;
        }

        label {
            font-weight: 700;
        }

        .alert {
            background: #392327;
            border: 1px solid #703a43;
            padding: 12px 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }

        .success {
            background: #20362a;
            border-color: #376b4b;
        }

        .avatar {
            width: 100px;
            height: 100px;
            object-fit: cover;
            border-radius: 50%;
            border: 2px solid #444;
        }

        footer {
            text-align: center;
            padding: 40px 20px;
            color: #777f8d;
        }
    </style>
</head>
<body>

<nav class="nav">
    <a class="logo" href="{{ url_for('index') }}">JFGK Studio</a>

    <div class="nav-links">
        <a href="{{ url_for('index') }}">Главная</a>
        <a href="{{ url_for('services') }}">Услуги</a>

        {% if session.get("user_id") %}
            <a href="{{ url_for('profile') }}">Профиль</a>
            <a href="{{ url_for('orders') }}">Заказы</a>
            <a href="{{ url_for('messages') }}">Сообщения</a>
            <a href="{{ url_for('logout') }}">Выйти</a>
        {% else %}
            <a href="{{ url_for('login') }}">Войти</a>
            <a href="{{ url_for('register') }}">Регистрация</a>
        {% endif %}
    </div>
</nav>

<div class="container">
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
                <div class="alert">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    {{ content|safe }}
</div>

<footer>
    JFGK Studio
</footer>

</body>
</html>
"""


def render_page(title, content):
    return render_template_string(
        BASE_HTML,
        title=title,
        content=content
    )


@app.route("/")
def index():
    content = """
    <section class="hero">
        <h1>JFGK Studio</h1>
        <p class="muted">
            Разработка сайтов, Python и цифровых решений.
        </p>

        <a class="btn" href="/services">Посмотреть услуги</a>

        {% if not session.get("user_id") %}
            <a class="btn dark" href="/register">Создать аккаунт</a>
        {% endif %}
    </section>
    """

    return render_page("JFGK Studio", content)


@app.route("/services")
def services():
    content = """
    <h1>Услуги</h1>

    <div class="grid">
        <div class="card">
            <h2>Разработка сайтов</h2>
            <p class="muted">
                Создание современных сайтов и веб-приложений.
            </p>
        </div>

        <div class="card">
            <h2>Python</h2>
            <p class="muted">
                Разработка приложений и автоматизация задач на Python.
            </p>
        </div>

        <div class="card">
            <h2>Flask</h2>
            <p class="muted">
                Создание серверных приложений и API на Flask.
            </p>
        </div>
    </div>
    """

    return render_page("Услуги", content)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()

        if not username or not password:
            return render_page(
                "Регистрация",
                """
                <div class="card">
                    <div class="alert">Заполните имя пользователя и пароль.</div>
                    <a class="btn" href="/register">Назад</a>
                </div>
                """
            )

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            conn.close()
            return render_page(
                "Регистрация",
                """
                <div class="card">
                    <div class="alert">Такой пользователь уже существует.</div>
                    <a class="btn" href="/register">Назад</a>
                </div>
                """
            )

        password_hash = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO users (username, password, email)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, email)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    content = """
    <div class="card">
        <h1>Регистрация</h1>

        <form method="post">
            <label>Имя пользователя</label>
            <input name="username" required>

            <label>Email</label>
            <input type="email" name="email">

            <label>Пароль</label>
            <input type="password" name="password" required>

            <button class="btn" type="submit">Создать аккаунт</button>
        </form>
    </div>
    """

    return render_page("Регистрация", content)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("profile"))

        return render_page(
            "Вход",
            """
            <div class="card">
                <div class="alert">Неверное имя пользователя или пароль.</div>
                <a class="btn" href="/login">Попробовать снова</a>
            </div>
            """
        )

    content = """
    <div class="card">
        <h1>Вход</h1>

        <form method="post">
            <label>Имя пользователя</label>
            <input name="username" required>

            <label>Пароль</label>
            <input type="password" name="password" required>

            <button class="btn" type="submit">Войти</button>
        </form>
    </div>
    """

    return render_page("Вход", content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    avatar_html = ""

    if user["avatar"]:
        avatar_html = f"""
        <img class="avatar"
             src="/static/uploads/{user['avatar']}"
             alt="Аватар">
        """

    content = f"""
    <div class="card">
        <h1>Профиль</h1>

        {avatar_html}

        <h2>{user["username"]}</h2>

        <p class="muted">
            Email: {user["email"] or "не указан"}
        </p>

        <p>
            {user["bio"] or "Описание профиля пока не добавлено."}
        </p>

        <a class="btn" href="/profile/edit">Редактировать профиль</a>
    </div>
    """

    return render_page("Профиль", content)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        bio = request.form.get("bio", "").strip()

        avatar = request.files.get("avatar")
        avatar_name = user["avatar"]

        if avatar and avatar.filename and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)

            unique_name = f"{session['user_id']}_{secrets.token_hex(8)}_{filename}"

            avatar.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    unique_name
                )
            )

            avatar_name = unique_name

        conn.execute(
            """
            UPDATE users
            SET email = ?, bio = ?, avatar = ?
            WHERE id = ?
            """,
            (
                email,
                bio,
                avatar_name,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("profile"))

    conn.close()

    content = f"""
    <div class="card">
        <h1>Редактирование профиля</h1>

        <form method="post" enctype="multipart/form-data">
            <label>Email</label>
            <input
                type="email"
                name="email"
                value="{user['email'] or ''}"
            >

            <label>О себе</label>
            <textarea name="bio">{user['bio'] or ''}</textarea>

            <label>Аватар</label>
            <input type="file" name="avatar" accept="image/*">

            <button class="btn" type="submit">
                Сохранить
            </button>
        </form>
    </div>
    """

    return render_page("Редактирование профиля", content)


@app.route("/orders")
@login_required
def orders():
    conn = get_db()

    orders_list = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    if not orders_list:
        orders_html = """
        <p class="muted">У вас пока нет заказов.</p>
        """
    else:
        orders_html = ""

        for order in orders_list:
            orders_html += f"""
            <div class="card">
                <h2>{order["service"]}</h2>
                <p>{order["description"] or ""}</p>
                <p class="muted">
                    Статус: {order["status"]}
                </p>
            </div>
            """

    content = f"""
    <h1>Мои заказы</h1>

    {orders_html}

    <a class="btn" href="/orders/new">Создать заказ</a>
    """

    return render_page("Заказы", content)


@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    if request.method == "POST":
        service = request.form.get("service", "").strip()
        description = request.form.get("description", "").strip()

        if not service:
            return render_page(
                "Новый заказ",
                """
                <div class="card">
                    <div class="alert">
                        Укажите услугу.
                    </div>
                </div>
                """
            )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO orders (user_id, service, description)
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                service,
                description
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("orders"))

    content = """
    <div class="card">
        <h1>Новый заказ</h1>

        <form method="post">
            <label>Услуга</label>
            <select name="service" required>
                <option value="">Выберите услугу</option>
                <option value="Разработка сайта">
                    Разработка сайта
                </option>
                <option value="Python">
                    Python
                </option>
                <option value="Flask">
                    Flask
                </option>
            </select>

            <label>Описание</label>
            <textarea
                name="description"
                placeholder="Опишите задачу"
            ></textarea>

            <button class="btn" type="submit">
                Отправить заказ
            </button>
        </form>
    </div>
    """

    return render_page("Новый заказ", content)


@app.route("/messages")
@login_required
def messages():
    conn = get_db()

    users = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE id != ?
        ORDER BY username
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    users_html = ""

    for user in users:
        users_html += f"""
        <div class="card">
            <h2>{user["username"]}</h2>
            <a class="btn" href="/messages/{user["id"]}">
                Открыть чат
            </a>
        </div>
        """

    if not users_html:
        users_html = """
        <div class="card">
            <p class="muted">
                Пока нет других пользователей.
            </p>
        </div>
        """

    return render_page("Сообщения", users_html)


@app.route("/messages/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat(user_id):
    conn = get_db()

    other_user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not other_user:
        conn.close()
        return "Пользователь не найден", 404

    if request.method == "POST":
        text = request.form.get("text", "").strip()

        if text:
            conn.execute(
                """
                INSERT INTO messages
                (sender_id, receiver_id, text)
                VALUES (?, ?, ?)
                """,
                (
                    session["user_id"],
                    user_id,
                    text
                )
            )

            conn.commit()

    chat_messages = conn.execute(
        """
        SELECT *
        FROM messages
        WHERE
            (sender_id = ? AND receiver_id = ?)
            OR
            (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at ASC
        """,
        (
            session["user_id"],
            user_id,
            user_id,
            session["user_id"]
        )
    ).fetchall()

    conn.close()

    messages_html = ""

    for message in chat_messages:
        side = "right" if message["sender_id"] == session["user_id"] else "left"

        messages_html += f"""
        <div style="text-align:{side}; margin:10px 0;">
            <span style="
                display:inline-block;
                background:#272c36;
                padding:10px 14px;
                border-radius:10px;
                max-width:80%;
            ">
                {message["text"]}
            </span>
        </div>
        """

    content = f"""
    <div class="card">
        <h1>Чат с {other_user["username"]}</h1>

        {messages_html}

        <form method="post">
            <textarea
                name="text"
                placeholder="Введите сообщение..."
                required
            ></textarea>

            <button class="btn" type="submit">
                Отправить
            </button>
        </form>
    </div>
    """

    return render_page(
        f"Чат с {other_user['username']}",
        content
    )


@app.route("/api/messages/<int:user_id>")
@login_required
def api_messages(user_id):
    conn = get_db()

    messages_data = conn.execute(
        """
        SELECT
            id,
            sender_id,
            receiver_id,
            text,
            created_at
        FROM messages
        WHERE
            (sender_id = ? AND receiver_id = ?)
            OR
            (sender_id = ? AND receiver_id = ?)
        ORDER BY created_at ASC
        """,
        (
            session["user_id"],
            user_id,
            user_id,
            session["user_id"]
        )
    ).fetchall()

    conn.close()

    return jsonify([
        dict(message)
        for message in messages_data
    ])


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Allow: /
Sitemap: /sitemap.xml
"""


@app.route("/sitemap.xml")
def sitemap():
    urls = [
        url_for("index", _external=True),
        url_for("services", _external=True),
        url_for("login", _external=True),
        url_for("register", _external=True)
    ]

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

    for site_url in urls:
        xml += f"""
    <url>
        <loc>{site_url}</loc>
    </url>
"""

    xml += """
</urlset>
"""

    return xml, 200, {"Content-Type": "application/xml"}


@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
)
