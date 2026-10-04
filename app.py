import os
import secrets
import sqlite3
from functools import wraps

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    render_template_string,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.secret_key = os.environ.get("JFGK_SECRET_KEY") or secrets.token_hex(32)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "site.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            account_type TEXT NOT NULL DEFAULT 'client',
            avatar TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            price TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Новая',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES users(id),
            FOREIGN KEY(provider_id) REFERENCES users(id),
            FOREIGN KEY(service_id) REFERENCES services(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()

    # Безопасное обновление старой базы, если она уже существовала.
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    if "account_type" not in columns:
        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN account_type TEXT NOT NULL DEFAULT 'client'
            """
        )

    conn.commit()
    conn.close()


init_db()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    conn.close()

    return user


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Сначала войдите в аккаунт.")
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def provider_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = current_user()

        if not user:
            return redirect(url_for("login"))

        if user["account_type"] != "provider":
            flash("Эта функция доступна только исполнителям.")
            return redirect(url_for("feed"))

        return func(*args, **kwargs)

    return wrapper


def client_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = current_user()

        if not user:
            return redirect(url_for("login"))

        if user["account_type"] != "client":
            flash("Эта функция доступна клиентам.")
            return redirect(url_for("feed"))

        return func(*args, **kwargs)

    return wrapper


BASE_TEMPLATE = """
<!DOCTYPE html>
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
            font-family:
                Inter,
                Arial,
                Helvetica,
                sans-serif;

            background:
                radial-gradient(
                    circle at top,
                    #202838 0%,
                    #0b0e13 45%,
                    #07090d 100%
                );

            color: #ffffff;
            min-height: 100vh;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        .nav {
            position: sticky;
            top: 0;
            z-index: 100;

            background: rgba(10, 13, 18, 0.92);
            backdrop-filter: blur(16px);

            border-bottom: 1px solid #242a35;

            padding: 15px 5%;

            display: flex;
            align-items: center;
            justify-content: space-between;

            gap: 20px;
        }

        .logo {
            font-size: 24px;
            font-weight: 900;
            letter-spacing: -1px;
        }

        .logo span {
            color: #8da8ff;
        }

        .nav-links {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .nav-links a {
            padding: 9px 12px;
            border-radius: 9px;
            color: #b9c0cc;
            font-size: 14px;
        }

        .nav-links a:hover {
            background: #191e27;
            color: #ffffff;
        }

        .container {
            width: min(1100px, 92%);
            margin: 35px auto 70px;
        }

        .hero {
            padding: 70px 25px;
            text-align: center;

            border: 1px solid #293140;
            border-radius: 24px;

            background:
                linear-gradient(
                    135deg,
                    rgba(38, 47, 65, 0.9),
                    rgba(17, 21, 29, 0.95)
                );

            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.25);
        }

        .hero h1 {
            font-size: clamp(42px, 8vw, 76px);
            margin: 0;
            letter-spacing: -4px;
        }

        .hero p {
            max-width: 650px;
            margin: 22px auto;
            line-height: 1.7;
            color: #aeb7c7;
        }

        h1 {
            letter-spacing: -1.5px;
        }

        h2,
        h3 {
            letter-spacing: -0.5px;
        }

        .muted {
            color: #9da7b7;
        }

        .grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(250px, 1fr));

            gap: 18px;
        }

        .card {
            background: rgba(20, 24, 32, 0.9);

            border: 1px solid #29303c;
            border-radius: 18px;

            padding: 22px;

            box-shadow:
                0 12px 40px rgba(0, 0, 0, 0.15);
        }

        .btn {
            display: inline-block;

            border: 0;
            cursor: pointer;

            padding: 11px 17px;

            border-radius: 10px;

            background: #ffffff;
            color: #11151c;

            font-weight: 800;

            transition: 0.2s;
        }

        .btn:hover {
            transform: translateY(-1px);
            opacity: 0.9;
        }

        .btn-dark {
            background: #252c38;
            color: #ffffff;
        }

        .btn-blue {
            background: #657eff;
            color: #ffffff;
        }

        .btn-red {
            background: #612d36;
            color: #ffffff;
        }

        form {
            margin: 0;
        }

        label {
            display: block;
            margin: 14px 0 7px;

            color: #d9dee7;
            font-weight: 700;
        }

        input,
        textarea,
        select {
            width: 100%;

            border: 1px solid #333b49;
            border-radius: 10px;

            background: #0d1016;
            color: #ffffff;

            padding: 13px;

            outline: none;
        }

        input:focus,
        textarea:focus,
        select:focus {
            border-color: #657eff;
        }

        textarea {
            min-height: 130px;
            resize: vertical;
        }

        .alert {
            padding: 13px 16px;
            margin-bottom: 15px;

            border-radius: 11px;

            background: #3c252b;
            border: 1px solid #68404a;
        }

        .post {
            overflow: hidden;
            padding: 0;
        }

        .post-body {
            padding: 20px;
        }

        .post-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
        }

        .avatar {
            width: 48px;
            height: 48px;

            border-radius: 50%;
            object-fit: cover;

            background: #272e39;

            border: 1px solid #394250;
        }

        .avatar-large {
            width: 100px;
            height: 100px;
        }

        .avatar-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;

            font-weight: 900;
            color: #dbe2ef;
        }

        .post-image {
            display: block;

            width: 100%;
            max-height: 600px;

            object-fit: cover;
        }

        .post-text {
            white-space: pre-wrap;
            line-height: 1.65;
            color: #e4e8ef;
        }

        .badge {
            display: inline-block;

            padding: 5px 9px;

            border-radius: 999px;

            background: #242c3a;
            color: #b9c8ff;

            font-size: 12px;
            font-weight: 700;
        }

        .feed {
            max-width: 720px;
            margin: 0 auto;
        }

        .two-column {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 22px;
        }

        .service-price {
            font-size: 20px;
            font-weight: 900;
            margin: 15px 0;
        }

        .profile-top {
            display: flex;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }

        .user-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .empty {
            text-align: center;
            padding: 45px 20px;
            color: #858e9d;
        }

        footer {
            text-align: center;
            padding: 35px;
            color: #667080;
        }

        .small {
            font-size: 13px;
        }

        @media (max-width: 760px) {
            .nav {
                align-items: flex-start;
                flex-direction: column;
            }

            .two-column {
                grid-template-columns: 1fr;
            }

            .hero {
                padding: 50px 20px;
            }

            .hero h1 {
                letter-spacing: -2px;
            }
        }
    </style>
</head>

<body>

<nav class="nav">

    <a class="logo" href="{{ url_for('index') }}">
        JFGK <span>Studio</span>
    </a>

    <div class="nav-links">

        <a href="{{ url_for('feed') }}">
            Лента
        </a>

        <a href="{{ url_for('services') }}">
            Услуги
        </a>

        {% if session.get("user_id") %}

            <a href="{{ url_for('profile') }}">
                Профиль
            </a>

            <a href="{{ url_for('orders') }}">
                Заявки
            </a>

            <a href="{{ url_for('messages') }}">
                Сообщения
            </a>

            <a href="{{ url_for('logout') }}">
                Выйти
            </a>

        {% else %}

            <a href="{{ url_for('login') }}">
                Войти
            </a>

            <a class="btn btn-blue" href="{{ url_for('register') }}">
                Регистрация
            </a>

        {% endif %}

    </div>

</nav>

<main class="container">

    {% with messages = get_flashed_messages() %}

        {% if messages %}

            {% for message in messages %}

                <div class="alert">
                    {{ message }}
                </div>

            {% endfor %}

        {% endif %}

    {% endwith %}

    {{ content|safe }}

</main>

<footer>
    JFGK Studio · Платформа для клиентов и специалистов
</footer>

</body>
</html>
"""


def page(title, content):
    return render_template_string(
        BASE_TEMPLATE,
        title=title,
        content=content,
    )


def avatar_html(user, large=False):
    size_class = "avatar-large" if large else ""

    if user["avatar"]:
        return f"""
        <img
            class="avatar {size_class}"
            src="{url_for('uploaded_file', filename=user['avatar'])}"
            alt="Аватар"
        >
        """

    letter = user["username"][0].upper()

    return f"""
    <div class="avatar avatar-placeholder {size_class}">
        {letter}
    </div>
    """


@app.route("/")
def index():
    content = """
    <section class="hero">

        <h1>JFGK Studio</h1>

        <p>
            Платформа, где клиенты находят специалистов,
            а специалисты показывают свои работы и услуги.
        </p>

        <div>
            <a class="btn btn-blue" href="/feed">
                Открыть ленту
            </a>

            <a class="btn btn-dark" href="/register">
                Создать аккаунт
            </a>
        </div>

    </section>

    <br>

    <div class="grid">

        <div class="card">
            <h2>Для клиентов</h2>
            <p class="muted">
                Находите специалистов, смотрите публикации,
                выбирайте услуги и отправляйте заявки.
            </p>
        </div>

        <div class="card">
            <h2>Для специалистов</h2>
            <p class="muted">
                Создавайте профиль, публикуйте работы,
                добавляйте услуги и получайте заявки.
            </p>
        </div>

        <div class="card">
            <h2>Общая лента</h2>
            <p class="muted">
                Делитесь фотографиями, текстами и своими проектами.
            </p>
        </div>

    </div>
    """

    return page("Главная", content)


@app.route("/feed")
def feed():
    conn = get_db()

    posts = conn.execute(
        """
        SELECT
            posts.*,
            users.username,
            users.account_type,
            users.avatar
        FROM posts
        JOIN users ON users.id = posts.user_id
        ORDER BY posts.created_at DESC
        """
    ).fetchall()

    conn.close()

    create_form = ""

    if session.get("user_id"):
        create_form = """
        <div class="card">

            <h2>Создать публикацию</h2>

            <form
                method="post"
                action="/post/create"
                enctype="multipart/form-data"
            >

                <label>Текст</label>

                <textarea
                    name="text"
                    placeholder="Что хотите рассказать?"
                    required
                ></textarea>

                <label>Фото</label>

                <input
                    type="file"
                    name="image"
                    accept="image/*"
                >

                <br><br>

                <button class="btn btn-blue" type="submit">
                    Опубликовать
                </button>

            </form>

        </div>

        <br>
        """

    posts_html = ""

    for post in posts:

        type_name = (
            "Предоставляющий услугу"
            if post["account_type"] == "provider"
            else "Клиент"
        )

        image_html = ""

        if post["image"]:
            image_html = f"""
            <img
                class="post-image"
                src="{url_for('uploaded_file', filename=post['image'])}"
                alt="Фото публикации"
            >
            """

        delete_html = ""

        if session.get("user_id") == post["user_id"]:
            delete_html = f"""
            <form
                method="post"
                action="/post/{post['id']}/delete"
                style="margin-top:15px;"
                onsubmit="return confirm('Удалить публикацию?');"
            >
                <button class="btn btn-red" type="submit">
                    Удалить
                </button>
            </form>
            """

        posts_html += f"""
        <article class="card post">

            {image_html}

            <div class="post-body">

                <div class="post-header">

                    <a href="/user/{post['user_id']}">
                        {avatar_html(post)}
                    </a>

                    <div>

                        <a href="/user/{post['user_id']}">
                            <strong>
                                {post['username']}
                            </strong>
                        </a>

                        <br>

                        <span class="badge">
                            {type_name}
                        </span>

                        <div class="muted small">
                            {post['created_at']}
                        </div>

                    </div>

                </div>

                <div class="post-text">
                    {post['text']}
                </div>

                {delete_html}

            </div>

        </article>

        <br>
        """

    if not posts_html:
        posts_html = """
        <div class="card empty">
            <h2>Лента пока пустая</h2>
            <p>
                Станьте первым, кто создаст публикацию.
            </p>
        </div>
        """

    content = f"""
    <div class="feed">

        <h1>Лента</h1>

        <p class="muted">
            Публикации клиентов и специалистов JFGK Studio.
        </p>

        {create_form}

        {posts_html}

    </div>
    """

    return page("Лента", content)


@app.route("/post/create", methods=["POST"])
@login_required
def create_post():
    text = request.form.get("text", "").strip()

    if not text:
        flash("Публикация не может быть пустой.")
        return redirect(url_for("feed"))

    image_name = None

    image = request.files.get("image")

    if image and image.filename:

        if not allowed_file(image.filename):
            flash("Можно загружать только изображения.")
            return redirect(url_for("feed"))

        original_name = secure_filename(image.filename)

        image_name = (
            f"{session['user_id']}_"
            f"{secrets.token_hex(10)}_"
            f"{original_name}"
        )

        image.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_name,
            )
        )

    conn = get_db()

    conn.execute(
        """
        INSERT INTO posts (user_id, text, image)
        VALUES (?, ?, ?)
        """,
        (
            session["user_id"],
            text,
            image_name,
        ),
    )

    conn.commit()
    conn.close()

    flash("Публикация опубликована.")

    return redirect(url_for("feed"))


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    conn = get_db()

    post = conn.execute(
        """
        SELECT *
        FROM posts
        WHERE id = ?
        """,
        (post_id,),
    ).fetchone()

    if not post:
        conn.close()
        abort(404)

    if post["user_id"] != session["user_id"]:
        conn.close()
        abort(403)

    if post["image"]:
        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            post["image"],
        )

        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass

    conn.execute(
        "DELETE FROM posts WHERE id = ?",
        (post_id,),
    )

    conn.commit()
    conn.close()

    flash("Публикация удалена.")

    return redirect(url_for("feed"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

        email = request.form.get(
            "email",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        account_type = request.form.get(
            "account_type",
            "client",
        )

        if account_type not in {"client", "provider"}:
            account_type = "client"

        if len(username) < 3:
            flash("Имя пользователя должно содержать минимум 3 символа.")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Пароль должен содержать минимум 6 символов.")
            return redirect(url_for("register"))

        conn = get_db()

        exists = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if exists:
            conn.close()

            flash("Такой пользователь уже существует.")

            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO users
            (
                username,
                password,
                email,
                account_type
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                email,
                account_type,
            ),
        )

        conn.commit()
        conn.close()

        flash("Аккаунт создан. Теперь войдите.")

        return redirect(url_for("login"))

    content = """
    <div class="card" style="max-width:650px;margin:auto;">

        <h1>Создание аккаунта</h1>

        <p class="muted">
            Выберите тип аккаунта.
        </p>

        <form method="post">

            <label>Тип аккаунта</label>

            <select name="account_type" required>

                <option value="client">
                    Клиент
                </option>

                <option value="provider">
                    Предоставляющий услугу
                </option>

            </select>

            <label>Имя пользователя</label>

            <input
                name="username"
                minlength="3"
                required
                placeholder="Ваше имя"
            >

            <label>Email</label>

            <input
                type="email"
                name="email"
                placeholder="example@mail.com"
            >

            <label>Пароль</label>

            <input
                type="password"
                name="password"
                minlength="6"
                required
            >

            <br>

            <button class="btn btn-blue" type="submit">
                Создать аккаунт
            </button>

        </form>

    </div>
    """

    return page("Регистрация", content)


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            "",
        ).strip()

        password = request.form.get(
            "password",
            "",
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password,
        ):
            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("feed"))

        flash("Неверное имя пользователя или пароль.")

    content = """
    <div class="card" style="max-width:500px;margin:auto;">

        <h1>Вход</h1>

        <form method="post">

            <label>Имя пользователя</label>

            <input
                name="username"
                required
            >

            <label>Пароль</label>

            <input
                type="password"
                name="password"
                required
            >

            <br>

            <button class="btn btn-blue" type="submit">
                Войти
            </button>

        </form>

    </div>
    """

    return page("Вход", content)


@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    return redirect(
        url_for(
            "user_profile",
            user_id=session["user_id"],
        )
    )


@app.route("/user/<int:user_id>")
def user_profile(user_id):

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if not user:
        conn.close()
        abort(404)

    posts = conn.execute(
        """
        SELECT *
        FROM posts
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()

    services_list = conn.execute(
        """
        SELECT *
        FROM services
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    type_name = (
        "Предоставляющий услугу"
        if user["account_type"] == "provider"
        else "Клиент"
    )

    posts_html = ""

    for post in posts:

        image_html = ""

        if post["image"]:
            image_html = f"""
            <img
                class="post-image"
                src="{url_for('uploaded_file', filename=post['image'])}"
            >
            """

        posts_html += f"""
        <article class="card post">

            {image_html}

            <div class="post-body">
                <div class="post-text">
                    {post['text']}
                </div>
            </div>

        </article>

        <br>
        """

    if not posts_html:
        posts_html = """
        <div class="card empty">
            Публикаций пока нет.
        </div>
        """

    services_html = ""

    for service in services_list:

        services_html += f"""
        <div class="card">

            <h2>
                {service['title']}
            </h2>

            <p class="muted">
                {service['description'] or ''}
            </p>

            <div class="service-price">
                {service['price'] or 'Цена по договорённости'}
            </div>

            {
                f'''
                <a
                    class="btn btn-blue"
                    href="/order/{service["id"]}"
                >
                    Заказать услугу
                </a>
                '''
                if session.get("user_id")
                and current_user()
                and current_user()["account_type"] == "client"
                and user["account_type"] == "provider"
                else ""
            }

        </div>
        """

    if user["account_type"] == "provider":
        services_section = f"""
        <h2>Услуги</h2>

        {services_html or '''
        <div class="card empty">
            У этого специалиста пока нет услуг.
        </div>
        '''}
        """
    else:
        services_section = ""

    message_button = ""

    if (
        session.get("user_id")
        and session["user_id"] != user_id
    ):
        message_button = f"""
        <a
            class="btn btn-blue"
            href="/messages/{user_id}"
        >
            Написать сообщение
        </a>
        """

    content = f"""
    <div class="card">

        <div class="profile-top">

            {avatar_html(user, large=True)}

            <div>

                <h1>
                    {user['username']}
                </h1>

                <span class="badge">
                    {type_name}
                </span>

                <p class="muted">
                    {user['bio'] or 'Пользователь пока не добавил описание.'}
                </p>

                {message_button}

            </div>

        </div>

    </div>

    {services_section}

    <h2>Публикации</h2>

    {posts_html}
    """

    return page(
        f"Профиль {user['username']}",
        content,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],),
    ).fetchone()

    if request.method == "POST":

        email = request.form.get(
            "email",
            "",
        ).strip()

        bio = request.form.get(
            "bio",
            "",
        ).strip()

        avatar_name = user["avatar"]

        avatar = request.files.get("avatar")

        if avatar and avatar.filename:

            if not allowed_file(avatar.filename):
                flash("Неверный формат изображения.")

                conn.close()

                return redirect(
                    url_for("edit_profile")
                )

            filename = secure_filename(
                avatar.filename
            )

            avatar_name = (
                f"{session['user_id']}_"
                f"{secrets.token_hex(10)}_"
                f"{filename}"
            )

            avatar.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    avatar_name,
                )
            )

        conn.execute(
            """
            UPDATE users
            SET email = ?,
                bio = ?,
                avatar = ?
            WHERE id = ?
            """,
            (
                email,
                bio,
                avatar_name,
                session["user_id"],
            ),
        )

        conn.commit()
        conn.close()

        flash("Профиль обновлён.")

        return redirect(url_for("profile"))

    conn.close()

    content = f"""
    <div class="card" style="max-width:650px;margin:auto;">

        <h1>Редактирование профиля</h1>

        <form
            method="post"
            enctype="multipart/form-data"
        >

            <label>Email</label>

            <input
                type="email"
                name="email"
                value="{user['email'] or ''}"
            >

            <label>О себе</label>

            <textarea name="bio">{user['bio'] or ''}</textarea>

            <label>Аватар</label>

            <input
                type="file"
                name="avatar"
                accept="image/*"
            >

            <br>

            <button class="btn btn-blue" type="submit">
                Сохранить
            </button>

        </form>

    </div>
    """

    return page("Редактирование профиля", content)


@app.route("/services")
def services():

    conn = get_db()

    services_list = conn.execute(
        """
        SELECT
            services.*,
            users.username,
            users.avatar
        FROM services
        JOIN users
            ON users.id = services.user_id
        ORDER BY services.created_at DESC
        """
    ).fetchall()

    conn.close()

    services_html = ""

    for service in services_list:

        services_html += f"""
        <div class="card">

            <div class="user-row">

                <a href="/user/{service['user_id']}">
                    {avatar_html(service)}
                </a>

                <div>
                    <a href="/user/{service['user_id']}">
                        <strong>
                            {service['username']}
                        </strong>
                    </a>

                    <br>

                    <span class="badge">
                        Специалист
                    </span>
                </div>

            </div>

            <h2>
                {service['title']}
            </h2>

            <p class="muted">
                {service['description'] or ''}
            </p>

            <div class="service-price">
                {service['price'] or 'Цена по договорённости'}
            </div>

            {
                f'''
                <a
                    class="btn btn-blue"
                    href="/order/{service["id"]}"
                >
                    Заказать
                </a>
                '''
                if session.get("user_id")
                and current_user()
                and current_user()["account_type"] == "client"
                else ""
            }

        </div>
        """

    if not services_html:
        services_html = """
        <div class="card empty">
            Пока никто не добавил услугу.
        </div>
        """

    add_service = ""

    user = current_user()

    if user and user["account_type"] == "provider":
        add_service = """
        <a
            class="btn btn-blue"
            href="/service/create"
        >
            Добавить услугу
        </a>
        """

    content = f"""
    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:15px;
        flex-wrap:wrap;
    ">

        <div>
            <h1>Услуги</h1>

            <p class="muted">
                Найдите специалиста для своей задачи.
            </p>
        </div>

        {add_service}

    </div>

    <br>

    <div class="grid">
        {services_html}
    </div>
    """

    return page("Услуги", content)


@app.route("/service/create", methods=["GET", "POST"])
@provider_required
def create_service():

    if request.method == "POST":

        title = request.form.get(
            "title",
            "",
        ).strip()

        description = request.form.get(
            "description",
            "",
        ).strip()

        price = request.form.get(
            "price",
            "",
        ).strip()

        if not title:
            flash("Название услуги обязательно.")

            return redirect(
                url_for("create_service")
            )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO services
            (
                user_id,
                title,
                description,
                price
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                description,
                price,
            ),
        )

        conn.commit()
        conn.close()

        flash("Услуга добавлена.")

        return redirect(
            url_for("services")
        )

    content = """
    <div class="card" style="max-width:700px;margin:auto;">

        <h1>Добавить услугу</h1>

        <form method="post">

            <label>Название услуги</label>

            <input
                name="title"
                placeholder="Например: Создание сайта"
                required
            >

            <label>Описание</label>

            <textarea
                name="description"
                placeholder="Расскажите, что входит в услугу"
            ></textarea>

            <label>Цена</label>

            <input
                name="price"
                placeholder="Например: от 10 000 ₽"
            >

            <br>

            <button class="btn btn-blue" type="submit">
                Добавить услугу
            </button>

        </form>

    </div>
    """

    return page(
        "Добавить услугу",
        content,
    )


@app.route("/order/<int:service_id>", methods=["GET", "POST"])
@client_required
def create_order(service_id):

    conn = get_db()

    service = conn.execute(
        """
        SELECT
            services.*,
            users.username
        FROM services
        JOIN users
            ON users.id = services.user_id
        WHERE services.id = ?
        """,
        (service_id,),
    ).fetchone()

    if not service:
        conn.close()
        abort(404)

    if request.method == "POST":

        description = request.form.get(
            "description",
            "",
        ).strip()

        conn.execute(
            """
            INSERT INTO orders
            (
                client_id,
                provider_id,
                service_id,
                description
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                session["user_id"],
                service["user_id"],
                service_id,
                description,
            ),
        )

        conn.commit()
        conn.close()

        flash("Заявка отправлена специалисту.")

        return redirect(
            url_for("orders")
        )

    conn.close()

    content = f"""
    <div class="card" style="max-width:700px;margin:auto;">

        <h1>
            Заказать: {service['title']}
        </h1>

        <p class="muted">
            Специалист: {service['username']}
        </p>

        <p>
            {service['description'] or ''}
        </p>

        <strong>
            {service['price'] or 'Цена по договорённости'}
        </strong>

        <br><br>

        <form method="post">

            <label>
                Что нужно сделать?
            </label>

            <textarea
                name="description"
                placeholder="Опишите вашу задачу"
                required
            ></textarea>

            <button
                class="btn btn-blue"
                type="submit"
            >
                Отправить заявку
            </button>

        </form>

    </div>
    """

    return page(
        "Заказ услуги",
        content,
    )


@app.route("/orders")
@login_required
def orders():

    user = current_user()

    conn = get_db()

    if user["account_type"] == "client":

        orders_list = conn.execute(
            """
            SELECT
                orders.*,
                services.title,
                users.username AS provider_name
            FROM orders
            JOIN services
                ON services.id = orders.service_id
            JOIN users
                ON users.id = orders.provider_id
            WHERE orders.client_id = ?
            ORDER BY orders.created_at DESC
            """,
            (session["user_id"],),
        ).fetchall()

        title = "Мои заявки"

        items_html = ""

        for order in orders_list:

            items_html += f"""
            <div class="card">

                <h2>
                    {order['title']}
                </h2>

                <p>
                    Специалист:
                    <strong>
                        {order['provider_name']}
                    </strong>
                </p>

                <p class="muted">
                    {order['description'] or ''}
                </p>

                <span class="badge">
                    {order['status']}
                </span>

            </div>

            <br>
            """

    else:

        orders_list = conn.execute(
            """
            SELECT
                orders.*,
                services.title,
                users.username AS client_name
            FROM orders
            JOIN services
                ON services.id = orders.service_id
            JOIN users
                ON users.id = orders.client_id
            WHERE orders.provider_id = ?
            ORDER BY orders.created_at DESC
            """,
            (session["user_id"],),
        ).fetchall()

        title = "Заявки клиентов"

        items_html = ""

        for order in orders_list:

            items_html += f"""
            <div class="card">

                <h2>
                    {order['title']}
                </h2>

                <p>
                    Клиент:
                    <strong>
                        {order['client_name']}
                    </strong>
                </p>

                <p class="muted">
                    {order['description'] or ''}
                </p>

                <span class="badge">
                    {order['status']}
                </span>

            </div>

            <br>
            """

    conn.close()

    if not items_html:
        items_html = """
        <div class="card empty">
            Заявок пока нет.
        </div>
        """

    content = f"""
    <h1>{title}</h1>

    {items_html}
    """

    return page(
        title,
        content,
    )


@app.route("/messages")
@login_required
def messages():

    conn = get_db()

    users = conn.execute(
        """
        SELECT
            id,
            username,
            account_type,
            avatar
        FROM users
        WHERE id != ?
        ORDER BY username
        """,
        (session["user_id"],),
    ).fetchall()

    conn.close()

    users_html = ""

    for user in users:

        type_name = (
            "Специалист"
            if user["account_type"] == "provider"
            else "Клиент"
        )

        users_html += f"""
        <div class="card">

            <div class="user-row">

                {avatar_html(user)}

                <div>

                    <a href="/user/{user['id']}">
                        <strong>
                            {user['username']}
                        </strong>
                    </a>

                    <br>

                    <span class="badge">
                        {type_name}
                    </span>

                </div>

            </div>

            <br>

            <a
                class="btn btn-blue"
                href="/messages/{user['id']}"
            >
                Написать
            </a>

        </div>
        """

    if not users_html:
        users_html = """
        <div class="card empty">
            Пока нет других пользователей.
        </div>
        """

    content = f"""
    <h1>Сообщения</h1>

    <div class="grid">
        {users_html}
    </div>
    """

    return page(
        "Сообщения",
        content,
    )


@app.route("/messages/<int:user_id>", methods=["GET", "POST"])
@login_required
def chat(user_id):

    if user_id == session["user_id"]:
        return redirect(url_for("messages"))

    conn = get_db()

    other_user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if not other_user:
        conn.close()
        abort(404)

    if request.method == "POST":

        text = request.form.get(
            "text",
            "",
        ).strip()

        if text:

            conn.execute(
                """
                INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    text
                )
                VALUES (?, ?, ?)
                """,
                (
                    session["user_id"],
                    user_id,
                    text,
                ),
            )

            conn.commit()

    chat_messages = conn.execute(
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
        ORDER BY created_at ASC
        """,
        (
            session["user_id"],
            user_id,
            user_id,
            session["user_id"],
        ),
    ).fetchall()

    conn.close()

    messages_html = ""

    for message in chat_messages:

        mine = (
            message["sender_id"]
            == session["user_id"]
        )

        align = "right" if mine else "left"

        messages_html += f"""
        <div style="
            text-align:{align};
            margin:10px 0;
        ">

            <span style="
                display:inline-block;
                background:
                    {'#657eff' if mine else '#252b36'};
                padding:11px 15px;
                border-radius:12px;
                max-width:80%;
                text-align:left;
            ">
                {message['text']}
            </span>

        </div>
        """

    content = f"""
    <div class="card" style="max-width:800px;margin:auto;">

        <div class="user-row">

            {avatar_html(other_user)}

            <div>
                <h2>
                    {other_user['username']}
                </h2>
            </div>

        </div>

        <hr style="
            border:0;
            border-top:1px solid #2b313d;
            margin:20px 0;
        ">

        {messages_html}

        <form method="post">

            <textarea
                name="text"
                placeholder="Введите сообщение..."
                required
            ></textarea>

            <button
                class="btn btn-blue"
                type="submit"
            >
                Отправить
            </button>

        </form>

    </div>
    """

    return page(
        f"Чат — {other_user['username']}",
        content,
    )


@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return __import__("flask").send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
    )


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Allow: /
"""


@app.errorhandler(413)
def file_too_large(error):
    return page(
        "Файл слишком большой",
        """
        <div class="card">
            <h1>Файл слишком большой</h1>

            <p class="muted">
                Максимальный размер изображения — 10 МБ.
            </p>

            <a class="btn" href="/feed">
                Вернуться в ленту
            </a>
        </div>
        """,
    ), 413


if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            "5000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
