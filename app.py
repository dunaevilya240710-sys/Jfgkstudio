import os
import sqlite3
import uuid
from functools import wraps
from datetime import datetime

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    flash,
    render_template_string,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.environ.get(
    "JFGK_SECRET_KEY",
    "jfgk-development-secret-change-me"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
}

DATABASE = os.path.join(BASE_DIR, "jfgk.db")


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            account_type TEXT NOT NULL DEFAULT 'client',
            display_name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            service_category TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            image TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            UNIQUE(user_id, post_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            UNIQUE(follower_id, provider_id),
            FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            message TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(donor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    db.commit()
    db.close()


init_db()


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
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


def allowed_image(filename):
    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_image(file):
    if not file or not file.filename:
        return ""

    if not allowed_image(file.filename):
        return ""

    extension = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"

    file.save(
        os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename,
        )
    )

    return filename


def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


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

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: #0b0f14;
            color: #f4f6f8;
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        button,
        input,
        textarea,
        select {
            font: inherit;
        }

        .topbar {
            position: sticky;
            top: 0;
            z-index: 20;
            background: rgba(11, 15, 20, .95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid #202731;
        }

        .nav {
            max-width: 1050px;
            margin: auto;
            min-height: 64px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 18px;
            gap: 20px;
        }

        .logo {
            font-size: 22px;
            font-weight: 900;
            letter-spacing: -.8px;
        }

        .logo span {
            color: #7c5cff;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 8px;
            overflow-x: auto;
        }

        .nav-links a {
            padding: 9px 12px;
            border-radius: 10px;
            color: #b9c0ca;
            white-space: nowrap;
            font-size: 14px;
        }

        .nav-links a:hover {
            background: #171d25;
            color: white;
        }

        .container {
            width: min(1050px, calc(100% - 28px));
            margin: 28px auto 80px;
        }

        .grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 310px;
            gap: 22px;
        }

        .card {
            background: #111720;
            border: 1px solid #202936;
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 16px;
        }

        .hero {
            padding: 28px;
            border-radius: 22px;
            background:
                radial-gradient(
                    circle at top right,
                    rgba(124,92,255,.3),
                    transparent 45%
                ),
                #111720;
            border: 1px solid #252e3b;
            margin-bottom: 20px;
        }

        h1,
        h2,
        h3 {
            margin-top: 0;
        }

        h1 {
            font-size: 34px;
            letter-spacing: -1.2px;
        }

        h2 {
            font-size: 24px;
        }

        .muted {
            color: #8993a1;
        }

        .small {
            font-size: 13px;
        }

        .btn {
            display: inline-flex;
            justify-content: center;
            align-items: center;
            border: 0;
            border-radius: 11px;
            padding: 10px 15px;
            background: #7c5cff;
            color: white;
            cursor: pointer;
            font-weight: 700;
        }

        .btn:hover {
            background: #6e4ef0;
        }

        .btn.secondary {
            background: #202936;
        }

        .btn.danger {
            background: #b9384b;
        }

        .btn.green {
            background: #238b67;
        }

        .btn.full {
            width: 100%;
        }

        form {
            margin: 0;
        }

        input,
        textarea,
        select {
            width: 100%;
            background: #0c1118;
            border: 1px solid #293341;
            border-radius: 11px;
            color: white;
            padding: 12px 13px;
            outline: none;
            margin-top: 6px;
            margin-bottom: 14px;
        }

        input:focus,
        textarea:focus,
        select:focus {
            border-color: #7c5cff;
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        label {
            color: #aeb7c3;
            font-size: 14px;
        }

        .post-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 13px;
        }

        .avatar {
            width: 46px;
            height: 46px;
            border-radius: 50%;
            object-fit: cover;
            background: #252e3b;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 800;
            flex-shrink: 0;
        }

        .avatar.large {
            width: 100px;
            height: 100px;
            font-size: 30px;
        }

        .avatar.xlarge {
            width: 130px;
            height: 130px;
            font-size: 38px;
        }

        .post-image {
            width: 100%;
            max-height: 600px;
            object-fit: cover;
            border-radius: 14px;
            margin-top: 10px;
        }

        .post-content {
            white-space: pre-wrap;
            line-height: 1.6;
            color: #e7ebef;
        }

        .post-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 15px;
        }

        .icon-btn {
            border: 0;
            background: #1a212b;
            color: #cbd2db;
            border-radius: 10px;
            padding: 9px 12px;
            cursor: pointer;
        }

        .icon-btn:hover {
            background: #252e3b;
        }

        .liked {
            color: #ff6179;
        }

        .profile-top {
            display: flex;
            gap: 22px;
            align-items: center;
        }

        .profile-info {
            flex: 1;
        }

        .profile-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
        }

        .tag {
            display: inline-block;
            padding: 5px 9px;
            border-radius: 999px;
            background: #25203d;
            color: #bcaeff;
            font-size: 12px;
        }

        .user-row {
            display: flex;
            gap: 12px;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #202731;
        }

        .user-row:last-child {
            border-bottom: 0;
        }

        .user-row .grow {
            flex: 1;
        }

        .flash {
            padding: 12px 14px;
            background: #18202a;
            border: 1px solid #293341;
            border-radius: 12px;
            margin-bottom: 14px;
        }

        .flash.error {
            border-color: #8c3343;
            background: #321821;
        }

        .flash.success {
            border-color: #27775d;
            background: #142a23;
        }

        .chat-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .chat-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 13px;
            border-radius: 13px;
            background: #171e27;
        }

        .chat-item:hover {
            background: #202936;
        }

        .messages {
            display: flex;
            flex-direction: column;
            gap: 8px;
            min-height: 350px;
            max-height: 600px;
            overflow-y: auto;
            padding: 10px 0;
        }

        .message {
            max-width: 75%;
            padding: 10px 13px;
            border-radius: 14px;
            background: #202936;
            align-self: flex-start;
        }

        .message.mine {
            background: #6247cf;
            align-self: flex-end;
        }

        .message-time {
            display: block;
            opacity: .65;
            font-size: 10px;
            margin-top: 4px;
        }

        .stats {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }

        .stat strong {
            display: block;
            font-size: 20px;
        }

        .empty {
            padding: 45px 20px;
            text-align: center;
            color: #7f8996;
        }

        .two {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .donate-box {
            text-align: center;
            padding: 25px;
        }

        .amounts {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 14px;
        }

        .amounts button {
            border: 1px solid #303a48;
            background: #171e27;
            color: white;
            padding: 10px;
            border-radius: 10px;
            cursor: pointer;
        }

        .amounts button:hover {
            border-color: #7c5cff;
        }

        @media (max-width: 800px) {
            .grid {
                grid-template-columns: 1fr;
            }

            .profile-top {
                align-items: flex-start;
            }

            .nav {
                align-items: flex-start;
                flex-direction: column;
                padding: 12px 14px;
                gap: 8px;
            }

            .nav-links {
                width: 100%;
            }
        }

        @media (max-width: 500px) {
            .container {
                width: min(100% - 18px, 1050px);
                margin-top: 18px;
            }

            .card {
                border-radius: 14px;
                padding: 14px;
            }

            .hero {
                padding: 20px;
            }

            h1 {
                font-size: 28px;
            }

            .profile-top {
                flex-direction: column;
            }

            .two {
                grid-template-columns: 1fr;
            }

            .amounts {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>

<body>

<header class="topbar">
    <nav class="nav">
        <a class="logo" href="{{ url_for('feed') }}">
            JFGK<span>Studio</span>
        </a>

        <div class="nav-links">
            {% if user %}
                <a href="{{ url_for('feed') }}">Лента</a>
                <a href="{{ url_for('explore') }}">Специалисты</a>
                <a href="{{ url_for('chats') }}">Чаты</a>
                <a href="{{ url_for('new_post') }}">+ Пост</a>
                <a href="{{ url_for('profile', username=user['username']) }}">
                    Профиль
                </a>
                <a href="{{ url_for('logout') }}">Выйти</a>
            {% else %}
                <a href="{{ url_for('login') }}">Войти</a>
                <a href="{{ url_for('register') }}">Регистрация</a>
            {% endif %}
        </div>
    </nav>
</header>

<main class="container">

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <div class="flash {{ category }}">
                {{ message }}
            </div>
        {% endfor %}
    {% endwith %}

    {{ body|safe }}

</main>

</body>
</html>
"""


def page(title, body, **context):
    user = current_user()

    html = render_template_string(
        BASE_HTML,
        title=title,
        body=body,
        user=user,
        **context
    )

    return html


@app.route("/")
def feed():
    db = get_db()

    posts = db.execute(
        """
        SELECT
            posts.*,
            users.username,
            users.display_name,
            users.avatar,
            users.account_type,
            (
                SELECT COUNT(*)
                FROM likes
                WHERE likes.post_id = posts.id
            ) AS likes_count,
            (
                SELECT COUNT(*)
                FROM likes
                WHERE likes.post_id = posts.id
                AND likes.user_id = ?
            ) AS liked
        FROM posts
        JOIN users ON users.id = posts.user_id
        ORDER BY posts.id DESC
        """,
        (session.get("user_id", 0),),
    ).fetchall()

    db.close()

    body = """
    <div class="hero">
        <h1>JFGK Studio</h1>
        <p class="muted">
            Сообщество клиентов и специалистов.
            Публикуйте работы, находите людей и общайтесь.
        </p>

        {% if not user %}
            <a class="btn" href="{{ url_for('register') }}">
                Создать аккаунт
            </a>
        {% endif %}
    </div>

    <div class="grid">
        <section>
            <div class="card">
                <h2>Лента публикаций</h2>
                <p class="muted">
                    Здесь появляются новые публикации участников.
                </p>
            </div>

            {% for post in posts %}
                <article class="card">

                    <div class="post-header">
                        {% if post['avatar'] %}
                            <img
                                class="avatar"
                                src="{{ url_for('uploaded_file', filename=post['avatar']) }}"
                            >
                        {% else %}
                            <div class="avatar">
                                {{ post['display_name'][0]|upper }}
                            </div>
                        {% endif %}

                        <div>
                            <a href="{{ url_for('profile', username=post['username']) }}">
                                <strong>{{ post['display_name'] }}</strong>
                            </a>

                            <div class="small muted">
                                @{{ post['username'] }}
                                {% if post['account_type'] == 'provider' %}
                                    · Специалист
                                {% else %}
                                    · Клиент
                                {% endif %}
                            </div>
                        </div>
                    </div>

                    <div class="post-content">
                        {{ post['content'] }}
                    </div>

                    {% if post['image'] %}
                        <img
                            class="post-image"
                            src="{{ url_for('uploaded_file', filename=post['image']) }}"
                        >
                    {% endif %}

                    <div class="post-actions">

                        {% if user %}
                            <form
                                method="post"
                                action="{{ url_for('like_post', post_id=post['id']) }}"
                            >
                                <button
                                    class="icon-btn {% if post['liked'] %}liked{% endif %}"
                                    type="submit"
                                >
                                    ♥ {{ post['likes_count'] }}
                                </button>
                            </form>
                        {% else %}
                            <span class="icon-btn">
                                ♥ {{ post['likes_count'] }}
                            </span>
                        {% endif %}

                        <a
                            class="icon-btn"
                            href="{{ url_for('profile', username=post['username']) }}"
                        >
                            Профиль
                        </a>
                    </div>

                    <div class="small muted" style="margin-top:10px">
                        {{ post['created_at'] }}
                    </div>

                </article>
            {% else %}
                <div class="card empty">
                    Пока нет публикаций.
                    Создайте первую!
                </div>
            {% endfor %}
        </section>

        <aside>
            <div class="card">
                <h3>JFGK Studio</h3>
                <p class="muted">
                    Найдите специалиста или расскажите о своей работе.
                </p>

                <a class="btn full" href="{{ url_for('explore') }}">
                    Найти специалиста
                </a>
            </div>
        </aside>
    </div>
    """

    return page("Лента", render_template_string(body, posts=posts))


@app.route("/explore")
def explore():
    db = get_db()

    providers = db.execute(
        """
        SELECT
            users.*,
            (
                SELECT COUNT(*)
                FROM follows
                WHERE follows.provider_id = users.id
            ) AS followers
        FROM users
        WHERE users.account_type = 'provider'
        ORDER BY followers DESC, users.id DESC
        """
    ).fetchall()

    db.close()

    body = """
    <div class="card">
        <h1>Специалисты</h1>
        <p class="muted">
            Люди, которые предлагают услуги в JFGK Studio.
        </p>
    </div>

    {% for person in providers %}
        <div class="card">
            <div class="user-row">

                {% if person['avatar'] %}
                    <img
                        class="avatar"
                        src="{{ url_for('uploaded_file', filename=person['avatar']) }}"
                    >
                {% else %}
                    <div class="avatar">
                        {{ person['display_name'][0]|upper }}
                    </div>
                {% endif %}

                <div class="grow">
                    <a href="{{ url_for('profile', username=person['username']) }}">
                        <strong>{{ person['display_name'] }}</strong>
                    </a>

                    <div class="small muted">
                        @{{ person['username'] }}
                    </div>

                    {% if person['service_category'] %}
                        <span class="tag">
                            {{ person['service_category'] }}
                        </span>
                    {% endif %}

                    <div class="small muted" style="margin-top:7px">
                        {{ person['followers'] }} подписчиков
                    </div>
                </div>

                <a
                    class="btn"
                    href="{{ url_for('profile', username=person['username']) }}"
                >
                    Открыть
                </a>
            </div>
        </div>
    {% else %}
        <div class="card empty">
            Пока нет зарегистрированных специалистов.
        </div>
    {% endfor %}
    """

    return page(
        "Специалисты",
        render_template_string(body, providers=providers)
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("feed"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        display_name = request.form.get("display_name", "").strip()
        account_type = request.form.get("account_type", "client")
        service_category = request.form.get(
            "service_category",
            ""
        ).strip()

        if not username or not email or not password or not display_name:
            flash("Заполните все обязательные поля.", "error")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("Имя пользователя должно быть не короче 3 символов.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Пароль должен быть не короче 6 символов.", "error")
            return redirect(url_for("register"))

        if account_type not in {"client", "provider"}:
            account_type = "client"

        if account_type != "provider":
            service_category = ""

        db = get_db()

        try:
            cursor = db.execute(
                """
                INSERT INTO users
                (
                    username,
                    email,
                    password,
                    account_type,
                    display_name,
                    service_category,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    email,
                    generate_password_hash(password),
                    account_type,
                    display_name,
                    service_category,
                    now(),
                ),
            )

            db.commit()
            user_id = cursor.lastrowid

        except sqlite3.IntegrityError:
            db.close()
            flash(
                "Такое имя пользователя или email уже используется.",
                "error"
            )
            return redirect(url_for("register"))

        db.close()

        session["user_id"] = user_id

        flash("Аккаунт создан!", "success")

        return redirect(url_for("feed"))

    body = """
    <div class="card" style="max-width:650px;margin:auto">
        <h1>Создание аккаунта</h1>

        <p class="muted">
            Выберите, кто вы в JFGK Studio.
        </p>

        <form method="post">

            <label>
                Отображаемое имя
                <input
                    name="display_name"
                    placeholder="Например, Илья"
                    required
                >
            </label>

            <label>
                Имя пользователя
                <input
                    name="username"
                    placeholder="ilya"
                    required
                >
            </label>

            <label>
                Email
                <input
                    type="email"
                    name="email"
                    placeholder="you@example.com"
                    required
                >
            </label>

            <label>
                Пароль
                <input
                    type="password"
                    name="password"
                    placeholder="Минимум 6 символов"
                    required
                >
            </label>

            <label>
                Тип аккаунта
                <select name="account_type" id="account_type">
                    <option value="client">
                        Клиент
                    </option>
                    <option value="provider">
                        Специалист
                    </option>
                </select>
            </label>

            <div id="serviceBox" style="display:none">
                <label>
                    Чем вы занимаетесь?
                    <input
                        name="service_category"
                        placeholder="Дизайн, фотография, ремонт..."
                    >
                </label>
            </div>

            <button class="btn full" type="submit">
                Создать аккаунт
            </button>
        </form>

        <p class="muted" style="margin-top:18px">
            Уже есть аккаунт?
            <a href="{{ url_for('login') }}" style="color:#a994ff">
                Войти
            </a>
        </p>
    </div>

    <script>
        const type = document.getElementById("account_type");
        const box = document.getElementById("serviceBox");

        function updateServiceBox() {
            box.style.display =
                type.value === "provider"
                    ? "block"
                    : "none";
        }

        type.addEventListener("change", updateServiceBox);
        updateServiceBox();
    </script>
    """

    return page(
        "Регистрация",
        render_template_string(body)
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("feed"))

    if request.method == "POST":
        login_value = request.form.get("login", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
               OR email = ?
            """,
            (login_value, login_value),
        ).fetchone()

        db.close()

        if not user or not check_password_hash(
            user["password"],
            password
        ):
            flash("Неверный логин или пароль.", "error")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]

        flash("Вы вошли в аккаунт.", "success")

        return redirect(url_for("feed"))

    body = """
    <div class="card" style="max-width:500px;margin:auto">
        <h1>Вход</h1>

        <form method="post">
            <label>
                Email или имя пользователя
                <input
                    name="login"
                    autocomplete="username"
                    required
                >
            </label>

            <label>
                Пароль
                <input
                    type="password"
                    name="password"
                    autocomplete="current-password"
                    required
                >
            </label>

            <button class="btn full" type="submit">
                Войти
            </button>
        </form>

        <p class="muted" style="margin-top:18px">
            Нет аккаунта?
            <a href="{{ url_for('register') }}" style="color:#a994ff">
                Зарегистрироваться
            </a>
        </p>
    </div>
    """

    return page(
        "Вход",
        render_template_string(body)
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("feed"))


@app.route("/profile/<username>")
def profile(username):
    db = get_db()

    person = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username.lower(),),
    ).fetchone()

    if not person:
        db.close()
        return "Пользователь не найден", 404

    posts = db.execute(
        """
        SELECT
            posts.*,
            (
                SELECT COUNT(*)
                FROM likes
                WHERE likes.post_id = posts.id
            ) AS likes_count,
            (
                SELECT COUNT(*)
                FROM likes
                WHERE likes.post_id = posts.id
                AND likes.user_id = ?
            ) AS liked
        FROM posts
        WHERE posts.user_id = ?
        ORDER BY posts.id DESC
        """,
        (
            session.get("user_id", 0),
            person["id"],
        ),
    ).fetchall()

    followers = db.execute(
        """
        SELECT COUNT(*)
        FROM follows
        WHERE provider_id = ?
        """,
        (person["id"],),
    ).fetchone()[0]

    following = False

    if session.get("user_id"):
        following = db.execute(
            """
            SELECT 1
            FROM follows
            WHERE follower_id = ?
              AND provider_id = ?
            """,
            (
                session["user_id"],
                person["id"],
            ),
        ).fetchone() is not None

    db.close()

    is_owner = (
        current_user()
        and current_user()["id"] == person["id"]
    )

    body = """
    <div class="card">
        <div class="profile-top">

            {% if person['avatar'] %}
                <img
                    class="avatar xlarge"
                    src="{{ url_for('uploaded_file', filename=person['avatar']) }}"
                >
            {% else %}
                <div class="avatar xlarge">
                    {{ person['display_name'][0]|upper }}
                </div>
            {% endif %}

            <div class="profile-info">
                <h1 style="margin-bottom:4px">
                    {{ person['display_name'] }}
                </h1>

                <div class="muted">
                    @{{ person['username'] }}
                </div>

                {% if person['account_type'] == 'provider' %}
                    <span class="tag" style="margin-top:10px">
                        Специалист
                    </span>

                    {% if person['service_category'] %}
                        <span class="tag" style="margin-top:10px">
                            {{ person['service_category'] }}
                        </span>
                    {% endif %}
                {% else %}
                    <span class="tag" style="margin-top:10px">
                        Клиент
                    </span>
                {% endif %}

                {% if person['bio'] %}
                    <p style="line-height:1.6">
                        {{ person['bio'] }}
                    </p>
                {% endif %}

                <div class="stats">
                    <div class="stat">
                        <strong>{{ posts|length }}</strong>
                        <span class="small muted">публикаций</span>
                    </div>

                    {% if person['account_type'] == 'provider' %}
                        <div class="stat">
                            <strong>{{ followers }}</strong>
                            <span class="small muted">подписчиков</span>
                        </div>
                    {% endif %}
                </div>

                <div class="profile-actions">

                    {% if is_owner %}
                        <a
                            class="btn"
                            href="{{ url_for('edit_profile') }}"
                        >
                            Редактировать профиль
                        </a>
                    {% else %}

                        {% if user %}
                            <form
                                method="post"
                                action="{{ url_for('follow', user_id=person['id']) }}"
                            >
                                {% if person['account_type'] == 'provider' %}
                                    <button
                                        class="btn {% if following %}secondary{% endif %}"
                                        type="submit"
                                    >
                                        {% if following %}
                                            Отписаться
                                        {% else %}
                                            Подписаться
                                        {% endif %}
                                    </button>
                                {% endif %}
                            </form>

                            <a
                                class="btn secondary"
                                href="{{ url_for('chat', user_id=person['id']) }}"
                            >
                                Написать
                            </a>

                            {% if person['account_type'] == 'provider' %}
                                <a
                                    class="btn green"
                                    href="{{ url_for('donate', user_id=person['id']) }}"
                                >
                                    ♥ Донат
                                </a>
                            {% endif %}

                        {% else %}
                            <a
                                class="btn"
                                href="{{ url_for('login') }}"
                            >
                                Войти, чтобы написать
                            </a>
                        {% endif %}

                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>Публикации</h2>
    </div>

    {% for post in posts %}
        <article class="card">

            <div class="post-header">
                {% if person['avatar'] %}
                    <img
                        class="avatar"
                        src="{{ url_for('uploaded_file', filename=person['avatar']) }}"
                    >
                {% else %}
                    <div class="avatar">
                        {{ person['display_name'][0]|upper }}
                    </div>
                {% endif %}

                <div>
                    <strong>{{ person['display_name'] }}</strong>
                    <div class="small muted">
                        {{ post['created_at'] }}
                    </div>
                </div>
            </div>

            <div class="post-content">
                {{ post['content'] }}
            </div>

            {% if post['image'] %}
                <img
                    class="post-image"
                    src="{{ url_for('uploaded_file', filename=post['image']) }}"
                >
            {% endif %}

            <div class="post-actions">
                {% if user %}
                    <form
                        method="post"
                        action="{{ url_for('like_post', post_id=post['id']) }}"
                    >
                        <button
                            class="icon-btn {% if post['liked'] %}liked{% endif %}"
                        >
                            ♥ {{ post['likes_count'] }}
                        </button>
                    </form>
                {% else %}
                    <span class="icon-btn">
                        ♥ {{ post['likes_count'] }}
                    </span>
                {% endif %}
            </div>
        </article>
    {% else %}
        <div class="card empty">
            У пользователя пока нет публикаций.
        </div>
    {% endfor %}
    """

    return page(
        person["display_name"],
        render_template_string(
            body,
            person=person,
            posts=posts,
            followers=followers,
            following=following,
            is_owner=is_owner,
        ),
    )


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = current_user()

    if request.method == "POST":
        display_name = request.form.get(
            "display_name",
            ""
        ).strip()

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        service_category = request.form.get(
            "service_category",
            ""
        ).strip()

        avatar = request.files.get("avatar")

        if not display_name:
            flash("Введите отображаемое имя.", "error")
            return redirect(url_for("edit_profile"))

        new_avatar = user["avatar"]

        if avatar and avatar.filename:
            saved = save_image(avatar)

            if not saved:
                flash(
                    "Не удалось загрузить аватар. "
                    "Используйте JPG, PNG, GIF или WEBP.",
                    "error",
                )
                return redirect(url_for("edit_profile"))

            new_avatar = saved

        if user["account_type"] != "provider":
            service_category = ""

        db = get_db()

        db.execute(
            """
            UPDATE users
            SET
                display_name = ?,
                bio = ?,
                avatar = ?,
                service_category = ?
            WHERE id = ?
            """,
            (
                display_name,
                bio,
                new_avatar,
                service_category,
                user["id"],
            ),
        )

        db.commit()
        db.close()

        flash("Профиль обновлён.", "success")

        return redirect(
            url_for(
                "profile",
                username=user["username"],
            )
        )

    body = """
    <div class="card" style="max-width:700px;margin:auto">
        <h1>Редактировать профиль</h1>

        <form
            method="post"
            enctype="multipart/form-data"
        >

            <label>
                Отображаемое имя
                <input
                    name="display_name"
                    value="{{ user['display_name'] }}"
                    required
                >
            </label>

            <label>
                О себе
                <textarea
                    name="bio"
                    placeholder="Расскажите о себе..."
                >{{ user['bio'] }}</textarea>
            </label>

            {% if user['account_type'] == 'provider' %}
                <label>
                    Услуга / специализация
                    <input
                        name="service_category"
                        value="{{ user['service_category'] }}"
                        placeholder="Например: фотограф"
                    >
                </label>
            {% endif %}

            <label>
                Аватар
                <input
                    type="file"
                    name="avatar"
                    accept="image/*"
                >
            </label>

            <button class="btn full" type="submit">
                Сохранить изменения
            </button>
        </form>
    </div>
    """

    return page(
        "Редактирование профиля",
        render_template_string(body, user=user),
    )


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    user = current_user()

    if request.method == "POST":
        content = request.form.get(
            "content",
            ""
        ).strip()

        image = request.files.get("image")

        if not content:
            flash("Напишите что-нибудь.", "error")
            return redirect(url_for("new_post"))

        image_name = ""

        if image and image.filename:
            image_name = save_image(image)

            if not image_name:
                flash(
                    "Неподдерживаемый формат изображения.",
                    "error",
                )
                return redirect(url_for("new_post"))

        db = get_db()

        db.execute(
            """
            INSERT INTO posts
            (
                user_id,
                content,
                image,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user["id"],
                content,
                image_name,
                now(),
            ),
        )

        db.commit()
        db.close()

        flash("Публикация опубликована.", "success")

        return redirect(url_for("feed"))

    body = """
    <div class="card" style="max-width:700px;margin:auto">
        <h1>Новая публикация</h1>

        <form
            method="post"
            enctype="multipart/form-data"
        >
            <label>
                Текст публикации
                <textarea
                    name="content"
                    placeholder="Что хотите рассказать?"
                    required
                ></textarea>
            </label>

            <label>
                Фотография
                <input
                    type="file"
                    name="image"
                    accept="image/*"
                >
            </label>

            <button class="btn full" type="submit">
                Опубликовать
            </button>
        </form>
    </div>
    """

    return page(
        "Новая публикация",
        render_template_string(body),
    )


@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    user = current_user()

    db = get_db()

    post = db.execute(
        "SELECT id FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()

    if not post:
        db.close()
        return redirect(url_for("feed"))

    existing = db.execute(
        """
        SELECT id
        FROM likes
        WHERE user_id = ?
          AND post_id = ?
        """,
        (
            user["id"],
            post_id,
        ),
    ).fetchone()

    if existing:
        db.execute(
            "DELETE FROM likes WHERE id = ?",
            (existing["id"],),
        )
    else:
        db.execute(
            """
            INSERT INTO likes
            (
                user_id,
                post_id
            )
            VALUES (?, ?)
            """,
            (
                user["id"],
                post_id,
            ),
        )

    db.commit()
    db.close()

    return request.referrer or redirect(url_for("feed"))


@app.route("/user/<int:user_id>/follow", methods=["POST"])
@login_required
def follow(user_id):
    user = current_user()

    if user["id"] == user_id:
        flash("Нельзя подписаться на самого себя.", "error")
        return redirect(request.referrer or url_for("feed"))

    db = get_db()

    target = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if not target:
        db.close()
        return redirect(url_for("feed"))

    if target["account_type"] != "provider":
        db.close()
        flash(
            "Подписываться можно только на специалистов.",
            "error",
        )
        return redirect(request.referrer or url_for("feed"))

    existing = db.execute(
        """
        SELECT id
        FROM follows
        WHERE follower_id = ?
          AND provider_id = ?
        """,
        (
            user["id"],
            user_id,
        ),
    ).fetchone()

    if existing:
        db.execute(
            "DELETE FROM follows WHERE id = ?",
            (existing["id"],),
        )
    else:
        db.execute(
            """
            INSERT INTO follows
            (
                follower_id,
                provider_id
            )
            VALUES (?, ?)
            """,
            (
                user["id"],
                user_id,
            ),
        )

    db.commit()
    db.close()

    return request.referrer or redirect(
        url_for(
            "profile",
            username=target["username"],
        )
    )


@app.route("/chats")
@login_required
def chats():
    user = current_user()

    db = get_db()

    conversations = db.execute(
        """
        SELECT
            other.id,
            other.username,
            other.display_name,
            other.avatar,
            other.account_type,
            MAX(messages.id) AS last_message_id
        FROM messages
        JOIN users AS other
            ON other.id =
                CASE
                    WHEN messages.sender_id = ?
                    THEN messages.receiver_id
                    ELSE messages.sender_id
                END
        WHERE messages.sender_id = ?
           OR messages.receiver_id = ?
        GROUP BY other.id
        ORDER BY last_message_id DESC
        """,
        (
            user["id"],
            user["id"],
            user["id"],
        ),
    ).fetchall()

    db.close()

    body = """
    <div class="card">
        <h1>Чаты</h1>
        <p class="muted">
            Ваши личные разговоры с участниками JFGK Studio.
        </p>
    </div>

    <div class="card">
        <div class="chat-list">

            {% for person in conversations %}
                <a
                    class="chat-item"
                    href="{{ url_for('chat', user_id=person['id']) }}"
                >

                    {% if person['avatar'] %}
                        <img
                            class="avatar"
                            src="{{ url_for('uploaded_file', filename=person['avatar']) }}"
                        >
                    {% else %}
                        <div class="avatar">
                            {{ person['display_name'][0]|upper }}
                        </div>
                    {% endif %}

                    <div>
                        <strong>{{ person['display_name'] }}</strong>

                        <div class="small muted">
                            @{{ person['username'] }}
                        </div>
                    </div>

                </a>
            {% else %}
                <div class="empty">
                    У вас пока нет чатов.
                    Откройте профиль пользователя и нажмите
                    «Написать».
                </div>
            {% endfor %}

        </div>
    </div>
    """

    return page(
        "Чаты",
        render_template_string(
            body,
            conversations=conversations,
        ),
    )


@app.route("/chat/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat(user_id):
    user = current_user()

    if user["id"] == user_id:
        return redirect(
            url_for(
                "profile",
                username=user["username"],
            )
        )

    db = get_db()

    target = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if not target:
        db.close()
        return "Пользователь не найден", 404

    if request.method == "POST":
        text_message = request.form.get(
            "message",
            ""
        ).strip()

        if text_message:
            db.execute(
                """
                INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    text,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    user["id"],
                    user_id,
                    text_message,
                    now(),
                ),
            )

            db.commit()

        db.close()

        return redirect(
            url_for(
                "chat",
                user_id=user_id,
            )
        )

    messages = db.execute(
        """
        SELECT *
        FROM messages
        WHERE
            (
                sender_id = ?
                AND receiver_id = ?
            )
            OR
            (
                sender_id = ?
                AND receiver_id = ?
            )
        ORDER BY id ASC
        """,
        (
            user["id"],
            user_id,
            user_id,
            user["id"],
        ),
    ).fetchall()

    db.execute(
        """
        UPDATE messages
        SET is_read = 1
        WHERE sender_id = ?
          AND receiver_id = ?
        """,
        (
            user_id,
            user["id"],
        ),
    )

    db.commit()
    db.close()

    body = """
    <div class="card">

        <div class="post-header">

            {% if target['avatar'] %}
                <img
                    class="avatar"
                    src="{{ url_for('uploaded_file', filename=target['avatar']) }}"
                >
            {% else %}
                <div class="avatar">
                    {{ target['display_name'][0]|upper }}
                </div>
            {% endif %}

            <div>
                <a
                    href="{{ url_for('profile', username=target['username']) }}"
                >
                    <strong>{{ target['display_name'] }}</strong>
                </a>

                <div class="small muted">
                    @{{ target['username'] }}
                </div>
            </div>

        </div>

        <div class="messages" id="messages">

            {% for message in messages %}
                <div
                    class="message
                    {% if message['sender_id'] == user['id'] %}
                        mine
                    {% endif %}"
                >
                    {{ message['text'] }}

                    <span class="message-time">
                        {{ message['created_at'] }}
                    </span>
                </div>
            {% else %}
                <div class="empty">
                    Начните общение.
                </div>
            {% endfor %}

        </div>

        <form method="post" style="display:flex;gap:8px">
            <input
                name="message"
                placeholder="Напишите сообщение..."
                autocomplete="off"
                style="margin:0"
                required
            >

            <button class="btn" type="submit">
                Отправить
            </button>
        </form>

    </div>

    <script>
        const messages = document.getElementById("messages");

        if (messages) {
            messages.scrollTop = messages.scrollHeight;
        }
    </script>
    """

    return page(
        f"Чат с {target['display_name']}",
        render_template_string(
            body,
            target=target,
            messages=messages,
        ),
    )


@app.route("/donate/<int:user_id>", methods=["GET", "POST"])
@login_required
def donate(user_id):
    user = current_user()

    if user["id"] == user_id:
        return redirect(
            url_for(
                "profile",
                username=user["username"],
            )
        )

    db = get_db()

    target = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    db.close()

    if not target:
        return "Пользователь не найден", 404

    if target["account_type"] != "provider":
        flash(
            "Донаты доступны специалистам.",
            "error",
        )
        return redirect(
            url_for(
                "profile",
                username=target["username"],
            )
        )

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        message = request.form.get(
            "message",
            ""
        ).strip()

        try:
            amount_rub = float(amount)
        except ValueError:
            amount_rub = 0

        if amount_rub < 10:
            flash(
                "Минимальная сумма доната — 10 ₽.",
                "error",
            )
            return redirect(
                url_for(
                    "donate",
                    user_id=user_id,
                )
            )

        amount_kopecks = int(amount_rub * 100)

        db = get_db()

        db.execute(
            """
            INSERT INTO donations
            (
                donor_id,
                receiver_id,
                amount,
                message,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                target["id"],
                amount_kopecks,
                message,
                "pending",
                now(),
            ),
        )

        db.commit()
        db.close()

        flash(
            "Заявка на донат создана. "
            "Для настоящей оплаты подключите платёжную систему.",
            "success",
        )

        return redirect(
            url_for(
                "profile",
                username=target["username"],
            )
        )

    body = """
    <div class="card donate-box" style="max-width:650px;margin:auto">

        {% if target['avatar'] %}
            <img
                class="avatar large"
                style="margin:auto"
                src="{{ url_for('uploaded_file', filename=target['avatar']) }}"
            >
        {% else %}
            <div class="avatar large" style="margin:auto">
                {{ target['display_name'][0]|upper }}
            </div>
        {% endif %}

        <h1 style="margin-top:18px">
            Поддержать {{ target['display_name'] }}
        </h1>

        <p class="muted">
            Оставьте донат специалисту и при желании
            добавьте сообщение.
        </p>

        <form method="post">

            <label>
                Сумма, ₽
                <input
                    type="number"
                    name="amount"
                    min="10"
                    step="1"
                    value="100"
                    required
                >
            </label>

            <div class="amounts">
                <button
                    type="button"
                    onclick="setAmount(100)"
                >
                    100 ₽
                </button>

                <button
                    type="button"
                    onclick="setAmount(250)"
                >
                    250 ₽
                </button>

                <button
                    type="button"
                    onclick="setAmount(500)"
                >
                    500 ₽
                </button>

                <button
                    type="button"
                    onclick="setAmount(1000)"
                >
                    1000 ₽
                </button>
            </div>

            <label>
                Сообщение
                <textarea
                    name="message"
                    placeholder="Напишите что-нибудь..."
                ></textarea>
            </label>

            <button class="btn green full" type="submit">
                Поддержать
            </button>
        </form>

        <p class="small muted" style="margin-top:15px">
            Сейчас это демонстрационная система.
            Для реального приёма платежей необходимо
            подключить платёжный сервис.
        </p>
    </div>

    <script>
        function setAmount(value) {
            document.querySelector(
                'input[name="amount"]'
            ).value = value;
        }
    </script>
    """

    return page(
        "Донат",
        render_template_string(
            body,
            target=target,
        ),
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
    )


@app.errorhandler(413)
def too_large(error):
    return page(
        "Файл слишком большой",
        """
        <div class="card">
            <h1>Файл слишком большой</h1>
            <p class="muted">
                Максимальный размер файла — 10 МБ.
            </p>
            <a class="btn" href="javascript:history.back()">
                Назад
            </a>
        </div>
        """,
    ), 413


@app.route("/health")
def health():
    return "JFGK Studio is running!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )