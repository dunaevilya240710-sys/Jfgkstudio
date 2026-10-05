import os
import sqlite3
import uuid
from functools import wraps
from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, flash, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.environ.get(
    "JFGK_SECRET_KEY",
    "jfgk-secret-key-change-this"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "jfgk.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            account_type TEXT NOT NULL DEFAULT 'client',
            avatar TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT DEFAULT '',
            image TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            PRIMARY KEY(user_id, post_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            follower_id INTEGER NOT NULL,
            specialist_id INTEGER NOT NULL,
            PRIMARY KEY(follower_id, specialist_id),
            FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(specialist_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            message TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(donor_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    db.commit()
    db.close()


init_db()


# ============================================================
# HELPERS
# ============================================================

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


def save_image(file):
    if not file or not file.filename:
        return ""

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_IMAGES:
        return ""

    new_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, new_name)
    file.save(path)

    return new_name


def is_following(follower_id, specialist_id):
    db = get_db()

    row = db.execute("""
        SELECT 1
        FROM follows
        WHERE follower_id = ? AND specialist_id = ?
    """, (follower_id, specialist_id)).fetchone()

    db.close()

    return row is not None


def post_liked(user_id, post_id):
    db = get_db()

    row = db.execute("""
        SELECT 1 FROM likes
        WHERE user_id = ? AND post_id = ?
    """, (user_id, post_id)).fetchone()

    db.close()

    return row is not None


# ============================================================
# TEMPLATE
# ============================================================

PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} — JFGK Studio</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f5f5f7;
    color: #171717;
}

a {
    color: inherit;
    text-decoration: none;
}

.nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: white;
    border-bottom: 1px solid #ddd;
    padding: 14px 20px;
}

.nav-inner {
    max-width: 1050px;
    margin: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
}

.logo {
    font-weight: 800;
    font-size: 22px;
}

.nav-links {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.nav-links a,
.btn {
    border: 0;
    border-radius: 10px;
    padding: 9px 14px;
    background: #111;
    color: white;
    cursor: pointer;
    font-size: 14px;
}

.btn-light {
    background: #eee !important;
    color: #111 !important;
}

.btn-danger {
    background: #d92d20 !important;
}

.btn-blue {
    background: #2563eb !important;
}

.container {
    max-width: 900px;
    margin: 30px auto;
    padding: 0 16px;
}

.card {
    background: white;
    border: 1px solid #ddd;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 18px;
    box-shadow: 0 3px 15px rgba(0,0,0,.04);
}

.center {
    text-align: center;
}

input,
textarea,
select {
    width: 100%;
    padding: 12px;
    margin: 7px 0 14px;
    border: 1px solid #ccc;
    border-radius: 10px;
    font: inherit;
}

textarea {
    min-height: 110px;
    resize: vertical;
}

.avatar {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    object-fit: cover;
    background: #ddd;
}

.avatar-big {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    object-fit: cover;
    background: #ddd;
}

.user-row {
    display: flex;
    align-items: center;
    gap: 13px;
}

.username {
    font-weight: 700;
}

.muted {
    color: #777;
}

.post-image {
    width: 100%;
    max-height: 600px;
    object-fit: contain;
    border-radius: 14px;
    margin-top: 12px;
    background: #eee;
}

.post-actions {
    display: flex;
    gap: 8px;
    margin-top: 14px;
    flex-wrap: wrap;
}

.inline {
    display: inline;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 15px;
}

.profile-header {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}

.badge {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    background: #eee;
    font-size: 12px;
}

.message {
    padding: 12px 15px;
    border-radius: 10px;
    margin-bottom: 10px;
    background: #e8f1ff;
}

.message.mine {
    background: #111;
    color: white;
    margin-left: 20%;
}

.chat-box {
    max-height: 500px;
    overflow-y: auto;
}

.flash {
    padding: 12px 15px;
    border-radius: 10px;
    background: #e8f5e9;
    margin-bottom: 15px;
}

.flash.error {
    background: #ffe7e7;
}

hr {
    border: 0;
    border-top: 1px solid #eee;
    margin: 20px 0;
}

h1, h2, h3 {
    margin-top: 0;
}

@media (max-width: 600px) {
    .nav-inner {
        align-items: flex-start;
        flex-direction: column;
    }

    .message.mine {
        margin-left: 5%;
    }
}
</style>
</head>

<body>

<nav class="nav">
    <div class="nav-inner">

        <a href="{{ url_for('home') }}" class="logo">
            JFGK Studio
        </a>

        <div class="nav-links">

            <a href="{{ url_for('home') }}">Лента</a>

            {% if user %}
                <a href="{{ url_for('specialists') }}">Специалисты</a>
                <a href="{{ url_for('chats') }}">Чаты</a>
                <a href="{{ url_for('profile', user_id=user['id']) }}">
                    Профиль
                </a>
                <a href="{{ url_for('logout') }}" class="btn-light">
                    Выйти
                </a>
            {% else %}
                <a href="{{ url_for('login') }}">Войти</a>
                <a href="{{ url_for('register') }}" class="btn">
                    Регистрация
                </a>
            {% endif %}

        </div>
    </div>
</nav>

<div class="container">

{% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
        <div class="flash {{ category }}">
            {{ message }}
        </div>
    {% endfor %}
{% endwith %}

{{ content|safe }}

</div>

</body>
</html>
"""


def render_page(title, content, **kwargs):
    return render_template_string(
        PAGE,
        title=title,
        content=render_template_string(content, **kwargs),
        user=current_user()
    )


# ============================================================
# HOME / FEED
# ============================================================

@app.route("/")
def home():
    db = get_db()

    posts = db.execute("""
        SELECT
            posts.*,
            users.username,
            users.name,
            users.avatar,
            users.account_type,
            (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.id) AS likes_count
        FROM posts
        JOIN users ON users.id = posts.user_id
        ORDER BY posts.id DESC
    """).fetchall()

    db.close()

    user = current_user()

    return render_page(
        "Лента",
        """
        <h1>Лента публикаций</h1>

        {% if user %}
            <div class="card">
                <h3>Новая публикация</h3>

                <form method="POST"
                      action="{{ url_for('create_post') }}"
                      enctype="multipart/form-data">

                    <textarea
                        name="text"
                        placeholder="Что хотите рассказать?"
                    ></textarea>

                    <label>Фотография</label>
                    <input type="file"
                           name="image"
                           accept="image/*">

                    <button class="btn" type="submit">
                        Опубликовать
                    </button>
                </form>
            </div>
        {% else %}
            <div class="card center">
                <h2>Добро пожаловать в JFGK Studio</h2>
                <p>Войдите или создайте аккаунт, чтобы публиковать записи.</p>
                <a class="btn" href="{{ url_for('register') }}">
                    Создать аккаунт
                </a>
            </div>
        {% endif %}

        {% for post in posts %}

            <div class="card">

                <div class="user-row">

                    {% if post['avatar'] %}
                        <img class="avatar"
                             src="{{ url_for('uploaded_file', filename=post['avatar']) }}">
                    {% else %}
                        <div class="avatar"></div>
                    {% endif %}

                    <div>
                        <a class="username"
                           href="{{ url_for('profile', user_id=post['user_id']) }}">
                            {{ post['name'] }}
                        </a>

                        <div class="muted">
                            @{{ post['username'] }}
                        </div>

                        {% if post['account_type'] == 'specialist' %}
                            <span class="badge">Специалист</span>
                        {% else %}
                            <span class="badge">Клиент</span>
                        {% endif %}
                    </div>

                </div>

                {% if post['text'] %}
                    <p style="white-space: pre-wrap;">
                        {{ post['text'] }}
                    </p>
                {% endif %}

                {% if post['image'] %}
                    <img class="post-image"
                         src="{{ url_for('uploaded_file', filename=post['image']) }}">
                {% endif %}

                <div class="post-actions">

                    {% if user %}

                        <form method="POST"
                              action="{{ url_for('like_post', post_id=post['id']) }}"
                              class="inline">

                            <button class="btn-light btn" type="submit">
                                {% if liked_posts.get(post['id']) %}
                                    ❤️
                                {% else %}
                                    ♡
                                {% endif %}
                                {{ post['likes_count'] }}
                            </button>

                        </form>

                    {% else %}
                        <span class="muted">
                            ❤️ {{ post['likes_count'] }}
                        </span>
                    {% endif %}

                    <a class="btn-light btn"
                       href="{{ url_for('profile', user_id=post['user_id']) }}">
                        Профиль
                    </a>

                </div>

            </div>

        {% else %}

            <div class="card center">
                <p>Публикаций пока нет.</p>
            </div>

        {% endfor %}
        """,
        posts=posts,
        liked_posts={
            p["id"]: post_liked(user["id"], p["id"])
            for p in posts
        } if user else {},
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        account_type = request.form.get("account_type", "client")

        if account_type not in ("client", "specialist"):
            account_type = "client"

        if not username or not password or not name:
            flash("Заполните все обязательные поля.", "error")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("Имя пользователя должно содержать минимум 3 символа.", "error")
            return redirect(url_for("register"))

        db = get_db()

        existing = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            db.close()
            flash("Такое имя пользователя уже занято.", "error")
            return redirect(url_for("register"))

        cursor = db.execute("""
            INSERT INTO users
            (username, password, name, account_type)
            VALUES (?, ?, ?, ?)
        """, (
            username,
            generate_password_hash(password),
            name,
            account_type
        ))

        db.commit()

        user_id = cursor.lastrowid

        db.close()

        session.clear()
        session["user_id"] = user_id

        flash("Аккаунт успешно создан!")

        return redirect(url_for("profile", user_id=user_id))

    return render_page(
        "Регистрация",
        """
        <div class="card">

            <h1>Создание аккаунта</h1>

            <form method="POST">

                <label>Имя</label>
                <input name="name" required>

                <label>Имя пользователя</label>
                <input
                    name="username"
                    placeholder="например: ivan123"
                    required
                >

                <label>Пароль</label>
                <input
                    type="password"
                    name="password"
                    required
                >

                <label>Тип аккаунта</label>

                <select name="account_type">

                    <option value="client">
                        Клиент
                    </option>

                    <option value="specialist">
                        Специалист
                    </option>

                </select>

                <button class="btn" type="submit">
                    Создать аккаунт
                </button>

            </form>

        </div>
        """
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        db.close()

        if not user or not check_password_hash(user["password"], password):
            flash("Неверное имя пользователя или пароль.", "error")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]

        flash("Вы успешно вошли.")

        return redirect(url_for("home"))

    return render_page(
        "Вход",
        """
        <div class="card">

            <h1>Вход</h1>

            <form method="POST">

                <label>Имя пользователя</label>
                <input name="username" required>

                <label>Пароль</label>
                <input
                    type="password"
                    name="password"
                    required
                >

                <button class="btn" type="submit">
                    Войти
                </button>

            </form>

        </div>
        """
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.")
    return redirect(url_for("home"))


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile/<int:user_id>")
def profile(user_id):

    db = get_db()

    profile_user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not profile_user:
        db.close()
        return "Пользователь не найден", 404

    posts = db.execute("""
        SELECT
            posts.*,
            (SELECT COUNT(*)
             FROM likes
             WHERE likes.post_id = posts.id) AS likes_count
        FROM posts
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    followers = db.execute("""
        SELECT COUNT(*) AS count
        FROM follows
        WHERE specialist_id = ?
    """, (user_id,)).fetchone()["count"]

    following = db.execute("""
        SELECT COUNT(*) AS count
        FROM follows
        WHERE follower_id = ?
    """, (user_id,)).fetchone()["count"]

    db.close()

    user = current_user()

    return render_page(
        "Профиль",
        """
        <div class="card">

            <div class="profile-header">

                {% if profile_user['avatar'] %}

                    <img
                        class="avatar-big"
                        src="{{ url_for('uploaded_file',
                                         filename=profile_user['avatar']) }}"
                    >

                {% else %}

                    <div class="avatar-big"></div>

                {% endif %}

                <div>

                    <h1>{{ profile_user['name'] }}</h1>

                    <p class="muted">
                        @{{ profile_user['username'] }}
                    </p>

                    {% if profile_user['account_type'] == 'specialist' %}
                        <span class="badge">
                            Специалист
                        </span>
                    {% else %}
                        <span class="badge">
                            Клиент
                        </span>
                    {% endif %}

                    {% if profile_user['bio'] %}
                        <p style="white-space: pre-wrap;">
                            {{ profile_user['bio'] }}
                        </p>
                    {% endif %}

                    <p>
                        Подписчики: <b>{{ followers }}</b>
                        &nbsp; · &nbsp;
                        Подписки: <b>{{ following }}</b>
                    </p>

                </div>

            </div>

            <hr>

            {% if user and user['id'] == profile_user['id'] %}

                <div class="grid">

                    <a class="btn"
                       href="{{ url_for('edit_profile') }}">
                        Редактировать профиль
                    </a>

                    <a class="btn btn-light"
                       href="{{ url_for('delete_account') }}">
                        Настройки аккаунта
                    </a>

                </div>

            {% elif user %}

                <div class="post-actions">

                    {% if profile_user['account_type'] == 'specialist' %}

                        <form method="POST"
                              action="{{ url_for('follow_user',
                                                 user_id=profile_user['id']) }}">

                            <button class="btn" type="submit">

                                {% if following_user %}
                                    Отписаться
                                {% else %}
                                    Подписаться
                                {% endif %}

                            </button>

                        </form>

                    {% endif %}

                    <a class="btn btn-blue"
                       href="{{ url_for('chat', user_id=profile_user['id']) }}">
                        Написать
                    </a>

                    <a class="btn"
                       href="{{ url_for('donate', user_id=profile_user['id']) }}">
                        Поддержать
                    </a>

                </div>

            {% else %}

                <a class="btn"
                   href="{{ url_for('login') }}">
                    Войти, чтобы взаимодействовать
                </a>

            {% endif %}

        </div>


        {% if user and user['id'] == profile_user['id'] %}

            <div class="card">

                <h2>Новая публикация</h2>

                <form method="POST"
                      action="{{ url_for('create_post') }}"
                      enctype="multipart/form-data">

                    <textarea
                        name="text"
                        placeholder="Напишите что-нибудь..."
                    ></textarea>

                    <input type="file"
                           name="image"
                           accept="image/*">

                    <button class="btn">
                        Опубликовать
                    </button>

                </form>

            </div>

        {% endif %}


        <h2>Публикации</h2>

        {% for post in posts %}

            <div class="card">

                {% if post['text'] %}
                    <p style="white-space: pre-wrap;">
                        {{ post['text'] }}
                    </p>
                {% endif %}

                {% if post['image'] %}

                    <img
                        class="post-image"
                        src="{{ url_for('uploaded_file',
                                         filename=post['image']) }}"
                    >

                {% endif %}

                <div class="post-actions">

                    {% if user %}

                        <form method="POST"
                              action="{{ url_for('like_post',
                                                 post_id=post['id']) }}">

                            <button class="btn-light btn">
                                {% if liked_posts.get(post['id']) %}
                                    ❤️
                                {% else %}
                                    ♡
                                {% endif %}

                                {{ post['likes_count'] }}
                            </button>

                        </form>

                    {% else %}

                        <span>
                            ❤️ {{ post['likes_count'] }}
                        </span>

                    {% endif %}

                </div>

            </div>

        {% else %}

            <div class="card">
                <p>Публикаций пока нет.</p>
            </div>

        {% endfor %}
        """,
        profile_user=profile_user,
        posts=posts,
        following_user=(
            user
            and user["id"] != profile_user["id"]
            and is_following(user["id"], profile_user["id"])
        ),
        liked_posts={
            p["id"]: post_liked(user["id"], p["id"])
            for p in posts
        } if user else {}
    )


# ============================================================
# EDIT PROFILE
# ============================================================

@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():

    user = current_user()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        bio = request.form.get("bio", "").strip()
        account_type = request.form.get("account_type", "client")

        if account_type not in ("client", "specialist"):
            account_type = "client"

        avatar = user["avatar"]

        uploaded = request.files.get("avatar")

        if uploaded and uploaded.filename:
            new_avatar = save_image(uploaded)

            if new_avatar:
                avatar = new_avatar
            else:
                flash("Недопустимый формат изображения.", "error")
                return redirect(url_for("edit_profile"))

        db = get_db()

        db.execute("""
            UPDATE users
            SET name = ?,
                bio = ?,
                account_type = ?,
                avatar = ?
            WHERE id = ?
        """, (
            name,
            bio,
            account_type,
            avatar,
            user["id"]
        ))

        db.commit()
        db.close()

        flash("Профиль обновлён.")

        return redirect(
            url_for("profile", user_id=user["id"])
        )

    return render_page(
        "Редактирование профиля",
        """
        <div class="card">

            <h1>Редактирование профиля</h1>

            <form method="POST"
                  enctype="multipart/form-data">

                <label>Имя</label>

                <input
                    name="name"
                    value="{{ user['name'] }}"
                    required
                >

                <label>О себе</label>

                <textarea name="bio">{{ user['bio'] }}</textarea>

                <label>Тип аккаунта</label>

                <select name="account_type">

                    <option value="client"
                        {% if user['account_type'] == 'client' %}
                            selected
                        {% endif %}>
                        Клиент
                    </option>

                    <option value="specialist"
                        {% if user['account_type'] == 'specialist' %}
                            selected
                        {% endif %}>
                        Специалист
                    </option>

                </select>

                <label>Аватар</label>

                <input
                    type="file"
                    name="avatar"
                    accept="image/*"
                >

                <button class="btn" type="submit">
                    Сохранить изменения
                </button>

            </form>

        </div>
        """,
        user=user
    )


# ============================================================
# CREATE POST
# ============================================================

@app.route("/create-post", methods=["POST"])
@login_required
def create_post():

    user = current_user()

    text = request.form.get("text", "").strip()

    image = save_image(request.files.get("image"))

    if not text and not image:
        flash("Добавьте текст или фотографию.", "error")
        return redirect(request.referrer or url_for("home"))

    db = get_db()

    db.execute("""
        INSERT INTO posts (user_id, text, image)
        VALUES (?, ?, ?)
    """, (
        user["id"],
        text,
        image
    ))

    db.commit()
    db.close()

    flash("Публикация добавлена.")

    return redirect(request.referrer or url_for("home"))


# ============================================================
# LIKE
# ============================================================

@app.route("/like/<int:post_id>", methods=["POST"])
@login_required
def like_post(post_id):

    user = current_user()

    db = get_db()

    post = db.execute(
        "SELECT id FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    if not post:
        db.close()
        return "Публикация не найдена", 404

    existing = db.execute("""
        SELECT 1
        FROM likes
        WHERE user_id = ? AND post_id = ?
    """, (
        user["id"],
        post_id
    )).fetchone()

    if existing:

        db.execute("""
            DELETE FROM likes
            WHERE user_id = ? AND post_id = ?
        """, (
            user["id"],
            post_id
        ))

    else:

        db.execute("""
            INSERT INTO likes (user_id, post_id)
            VALUES (?, ?)
        """, (
            user["id"],
            post_id
        ))

    db.commit()
    db.close()

    return redirect(request.referrer or url_for("home"))


# ============================================================
# FOLLOW SPECIALIST
# ============================================================

@app.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):

    user = current_user()

    if user["id"] == user_id:
        flash("Нельзя подписаться на самого себя.", "error")
        return redirect(url_for("profile", user_id=user_id))

    db = get_db()

    target = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not target:
        db.close()
        return "Пользователь не найден", 404

    if target["account_type"] != "specialist":
        db.close()
        flash("Подписываться можно только на специалистов.", "error")
        return redirect(url_for("profile", user_id=user_id))

    existing = db.execute("""
        SELECT 1
        FROM follows
        WHERE follower_id = ? AND specialist_id = ?
    """, (
        user["id"],
        user_id
    )).fetchone()

    if existing:

        db.execute("""
            DELETE FROM follows
            WHERE follower_id = ? AND specialist_id = ?
        """, (
            user["id"],
            user_id
        ))

        flash("Вы отписались от специалиста.")

    else:

        db.execute("""
            INSERT INTO follows
            (follower_id, specialist_id)
            VALUES (?, ?)
        """, (
            user["id"],
            user_id
        ))

        flash("Вы подписались на специалиста.")

    db.commit()
    db.close()

    return redirect(url_for("profile", user_id=user_id))


# ============================================================
# SPECIALISTS
# ============================================================

@app.route("/specialists")
def specialists():

    db = get_db()

    specialists_list = db.execute("""
        SELECT
            users.*,
            (
                SELECT COUNT(*)
                FROM follows
                WHERE follows.specialist_id = users.id
            ) AS followers
        FROM users
        WHERE account_type = 'specialist'
        ORDER BY followers DESC
    """).fetchall()

    db.close()

    return render_page(
        "Специалисты",
        """
        <h1>Специалисты</h1>

        <div class="grid">

        {% for specialist in specialists_list %}

            <div class="card">

                <div class="user-row">

                    {% if specialist['avatar'] %}

                        <img class="avatar"
                             src="{{ url_for(
                                 'uploaded_file',
                                 filename=specialist['avatar']
                             ) }}">

                    {% else %}

                        <div class="avatar"></div>

                    {% endif %}

                    <div>

                        <h3>
                            {{ specialist['name'] }}
                        </h3>

                        <div class="muted">
                            @{{ specialist['username'] }}
                        </div>

                    </div>

                </div>

                {% if specialist['bio'] %}
                    <p>
                        {{ specialist['bio'] }}
                    </p>
                {% endif %}

                <p>
                    Подписчиков:
                    <b>{{ specialist['followers'] }}</b>
                </p>

                <a class="btn"
                   href="{{ url_for(
                       'profile',
                       user_id=specialist['id']
                   ) }}">
                    Открыть профиль
                </a>

            </div>

        {% else %}

            <div class="card">
                <p>Специалистов пока нет.</p>
            </div>

        {% endfor %}

        </div>
        """,
        specialists_list=specialists_list
    )


# ============================================================
# DONATE
# ============================================================

@app.route("/donate/<int:user_id>", methods=["GET", "POST"])
@login_required
def donate(user_id):

    user = current_user()

    if user["id"] == user_id:
        flash("Нельзя отправить донат самому себе.", "error")
        return redirect(url_for("profile", user_id=user_id))

    db = get_db()

    recipient = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    db.close()

    if not recipient:
        return "Пользователь не найден", 404

    if request.method == "POST":

        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            amount = 0

        message = request.form.get("message", "").strip()

        if amount <= 0:
            flash("Введите корректную сумму.", "error")
            return redirect(
                url_for("donate", user_id=user_id)
            )

        db = get_db()

        db.execute("""
            INSERT INTO donations
            (donor_id, recipient_id, amount, message)
            VALUES (?, ?, ?, ?)
        """, (
            user["id"],
            recipient["id"],
            amount,
            message
        ))

        db.commit()
        db.close()

        flash(
            "Донат записан. Для реального перевода денег необходимо подключить платёжную систему."
        )

        return redirect(
            url_for("profile", user_id=user_id)
        )

    return render_page(
        "Поддержать",
        """
        <div class="card">

            <h1>Поддержать {{ recipient['name'] }}</h1>

            <p>
                Здесь можно указать сумму поддержки.
            </p>

            <p class="muted">
                Сейчас это внутренняя запись доната.
                Реальный перевод денег пока не подключён.
            </p>

            <form method="POST">

                <label>Сумма</label>

                <input
                    type="number"
                    name="amount"
                    min="1"
                    step="0.01"
                    placeholder="100"
                    required
                >

                <label>Сообщение</label>

                <textarea
                    name="message"
                    placeholder="Спасибо за вашу работу!"
                ></textarea>

                <button class="btn" type="submit">
                    Поддержать
                </button>

            </form>

        </div>
        """,
        recipient=recipient
    )


# ============================================================
# CHATS
# ============================================================

@app.route("/chats")
@login_required
def chats():

    user = current_user()

    db = get_db()

    people = db.execute("""
        SELECT DISTINCT
            u.id,
            u.username,
            u.name,
            u.avatar,
            u.account_type
        FROM users u
        JOIN messages m
        ON (
            (m.sender_id = ? AND m.receiver_id = u.id)
            OR
            (m.receiver_id = ? AND m.sender_id = u.id)
        )
        WHERE u.id != ?
        ORDER BY u.name
    """, (
        user["id"],
        user["id"],
        user["id"]
    )).fetchall()

    db.close()

    return render_page(
        "Чаты",
        """
        <h1>Чаты</h1>

        <div class="card">

        {% for person in people %}

            <a href="{{ url_for('chat', user_id=person['id']) }}">

                <div class="user-row"
                     style="padding:12px 0;">

                    {% if person['avatar'] %}

                        <img class="avatar"
                             src="{{ url_for(
                                 'uploaded_file',
                                 filename=person['avatar']
                             ) }}">

                    {% else %}

                        <div class="avatar"></div>

                    {% endif %}

                    <div>

                        <b>{{ person['name'] }}</b>

                        <div class="muted">
                            @{{ person['username'] }}
                        </div>

                    </div>

                </div>

            </a>

        {% else %}

            <p>
                У вас пока нет чатов.
            </p>

            <p>
                Откройте профиль пользователя и нажмите
                «Написать».
            </p>

        {% endfor %}

        </div>
        """,
        people=people
    )


@app.route("/chat/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat(user_id):

    user = current_user()

    if user["id"] == user_id:
        flash("Нельзя открыть чат с самим собой.", "error")
        return redirect(url_for("chats"))

    db = get_db()

    other = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not other:
        db.close()
        return "Пользователь не найден", 404

    if request.method == "POST":

        text = request.form.get("text", "").strip()

        if text:

            db.execute("""
                INSERT INTO messages
                (sender_id, receiver_id, text)
                VALUES (?, ?, ?)
            """, (
                user["id"],
                user_id,
                text
            ))

            db.commit()

    messages = db.execute("""
        SELECT
            messages.*,
            users.name,
            users.username
        FROM messages
        JOIN users
        ON users.id = messages.sender_id
        WHERE
            (
                messages.sender_id = ?
                AND messages.receiver_id = ?
            )
            OR
            (
                messages.sender_id = ?
                AND messages.receiver_id = ?
            )
        ORDER BY messages.id ASC
    """, (
        user["id"],
        user_id,
        user_id,
        user["id"]
    )).fetchall()

    db.close()

    return render_page(
        "Чат",
        """
        <div class="card">

            <div class="user-row">

                {% if other['avatar'] %}

                    <img class="avatar"
                         src="{{ url_for(
                             'uploaded_file',
                             filename=other['avatar']
                         ) }}">

                {% else %}

                    <div class="avatar"></div>

                {% endif %}

                <div>

                    <h2>
                        {{ other['name'] }}
                    </h2>

                    <div class="muted">
                        @{{ other['username'] }}
                    </div>

                </div>

            </div>

        </div>

        <div class="card chat-box">

            {% for message in messages %}

                <div class="
                    message
                    {% if message['sender_id'] == user['id'] %}
                        mine
                    {% endif %}
                ">

                    <b>
                        {{ message['name'] }}
                    </b>

                    <br>

                    {{ message['text'] }}

                </div>

            {% else %}

                <p class="muted">
                    Сообщений пока нет.
                </p>

            {% endfor %}

        </div>

        <div class="card">

            <form method="POST">

                <textarea
                    name="text"
                    placeholder="Введите сообщение..."
                    required
                ></textarea>

                <button class="btn btn-blue">
                    Отправить
                </button>

            </form>

        </div>
        """,
        other=other,
        messages=messages,
        user=user
    )


# ============================================================
# DELETE ACCOUNT
# ============================================================

@app.route("/delete-account", methods=["GET", "POST"])
@login_required
def delete_account():

    user = current_user()

    if request.method == "POST":

        password = request.form.get("password", "")

        if not check_password_hash(user["password"], password):
            flash("Неверный пароль.", "error")
            return redirect(url_for("delete_account"))

        db = get_db()

        db.execute(
            "DELETE FROM users WHERE id = ?",
            (user["id"],)
        )

        db.commit()
        db.close()

        session.clear()

        flash("Ваш аккаунт был удалён.")

        return redirect(url_for("home"))

    return render_page(
        "Удаление аккаунта",
        """
        <div class="card">

            <h1>Удаление аккаунта</h1>

            <p>
                Это действие удалит ваш аккаунт,
                публикации, лайки, подписки и сообщения.
            </p>

            <form method="POST">

                <label>
                    Введите пароль для подтверждения
                </label>

                <input
                    type="password"
                    name="password"
                    required
                >

                <button class="btn btn-danger">
                    Удалить аккаунт навсегда
                </button>

            </form>

        </div>
        """
    )


# ============================================================
# UPLOADS
# ============================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return "OK", 200


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )