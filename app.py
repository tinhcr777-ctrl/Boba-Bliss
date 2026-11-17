"""Boba Bliss: Flask pickup ordering with SQLite or PostgreSQL."""
import hmac
import os
import secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import click
from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
SIZES = {"Regular": 0, "Large": 100}
SWEETNESS = ("0%", "25%", "50%", "75%", "100%")
STATUSES = ("New", "Preparing", "Ready", "Completed", "Cancelled")
EMOJIS = ("🧋", "🍓", "🍵", "🥭", "🍑", "🍫", "🥥", "🫐")
SEED_DRINKS = [
    ("Brown Sugar Milk Tea", "Classic milk tea with brown sugar pearls.", 550, "🧋", 1),
    ("Strawberry Cloud", "Strawberry milk with a fluffy cream top.", 625, "🍓", 2),
    ("Matcha Dream", "Creamy matcha with a gentle earthy flavor.", 600, "🍵", 3),
    ("Mango Sunshine", "Fresh mango flavor with chewy boba.", 575, "🥭", 4),
    ("Peachy Tea", "Refreshing peach green tea.", 525, "🍑", 5),
    ("Chocolate Boba", "Sweet chocolate milk tea with pearls.", 625, "🍫", 6),
]


def create_app(test_config=None):
    app = Flask(__name__)
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]
    sqlite_path = os.environ.get("DATABASE_PATH") or str(BASE_DIR / "boba_bliss.db")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=sqlite_path,
        SQLALCHEMY_DATABASE_URI=database_url or "sqlite:///" + sqlite_path,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
        if "DATABASE" in test_config and "SQLALCHEMY_DATABASE_URI" not in test_config:
            app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + test_config["DATABASE"]

    orm = SQLAlchemy(app)

    class AppSetting(orm.Model):
        __tablename__ = "app_settings"
        key = orm.Column(orm.Text, primary_key=True)
        value = orm.Column(orm.Text, nullable=False)

    class Admin(orm.Model):
        __tablename__ = "admins"
        id = orm.Column(orm.Integer, primary_key=True)
        username = orm.Column(orm.Text, nullable=False, unique=True)
        password_hash = orm.Column(orm.Text, nullable=False)

    class Drink(orm.Model):
        __tablename__ = "drinks"
        id = orm.Column(orm.Integer, primary_key=True)
        name = orm.Column(orm.Text, nullable=False)
        description = orm.Column(orm.Text, nullable=False)
        price_cents = orm.Column(orm.Integer, nullable=False)
        emoji = orm.Column(orm.Text, nullable=False, default="🧋")
        sort_order = orm.Column(orm.Integer, nullable=False, default=0)
        available = orm.Column(orm.Integer, nullable=False, default=1)

    class Order(orm.Model):
        __tablename__ = "orders"
        id = orm.Column(orm.Integer, primary_key=True)
        customer_name = orm.Column(orm.Text, nullable=False)
        phone = orm.Column(orm.Text, nullable=False)
        drink_name = orm.Column(orm.Text, nullable=False)
        size = orm.Column(orm.Text, nullable=False)
        sweetness = orm.Column(orm.Text, nullable=False)
        quantity = orm.Column(orm.Integer, nullable=False)
        price_cents = orm.Column(orm.Integer, nullable=False)
        total_cents = orm.Column(orm.Integer, nullable=False)
        notes = orm.Column(orm.Text, nullable=False, default="")
        status = orm.Column(orm.Text, nullable=False, default="New")
        created_at = orm.Column(orm.Text, nullable=False)

    class QueryResult:
        def __init__(self, result):
            self.result = result
            self.rowcount = result.rowcount

        def fetchone(self):
            return self.result.mappings().fetchone()

        def fetchall(self):
            return self.result.mappings().fetchall()

    class DatabaseAdapter:
        """Keep beginner-friendly SQL calls working on both database engines."""
        def execute(self, query, values=()):
            params = {}
            for index, value in enumerate(values):
                marker = f"arg{index}"
                query = query.replace("?", ":" + marker, 1)
                params[marker] = value
            return QueryResult(orm.session.execute(text(query), params))

        def executemany(self, query, rows):
            rows = list(rows)
            if not rows:
                return
            count = len(rows[0])
            for index in range(count):
                query = query.replace("?", f":arg{index}", 1)
            orm.session.execute(
                text(query),
                [{f"arg{i}": value for i, value in enumerate(row)} for row in rows],
            )

        def commit(self):
            orm.session.commit()

    def get_db():
        return DatabaseAdapter()

    def init_db():
        orm.create_all()
        connection = get_db()
        if connection.execute("SELECT value FROM app_settings WHERE key='drinks_seeded'").fetchone() is None:
            connection.executemany(
                "INSERT INTO drinks(name,description,price_cents,emoji,sort_order) VALUES (?,?,?,?,?)",
                SEED_DRINKS,
            )
            connection.execute("INSERT INTO app_settings(key,value) VALUES ('drinks_seeded','yes')")
            connection.commit()

        # Bootstrap the first admin only. Never overwrite an existing password.
        bootstrap_user = os.environ.get("ADMIN_USERNAME", "").strip()
        bootstrap_password = os.environ.get("ADMIN_PASSWORD", "")
        if bootstrap_user and len(bootstrap_user) >= 3 and len(bootstrap_password) >= 12:
            existing = connection.execute("SELECT id FROM admins WHERE username=?", (bootstrap_user,)).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO admins(username,password_hash) VALUES (?,?)",
                    (bootstrap_user, generate_password_hash(bootstrap_password)),
                )
                connection.commit()

    @app.cli.command("create-admin")
    @click.option("--username", prompt="Admin username")
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, password):
        """Create or reset an admin account securely."""
        username = username.strip()
        if len(username) < 3 or len(password) < 8:
            raise click.ClickException("Username needs 3+ characters; password needs 8+ characters.")
        with app.app_context():
            db = get_db()
            db.execute(
                """INSERT INTO admins(username,password_hash) VALUES (?,?)
                   ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash""",
                (username, generate_password_hash(password)),
            )
            db.commit()
        click.echo(f"Admin '{username}' is ready.")

    @app.template_filter("money")
    def money(value):
        return f"${value / 100:.2f}"

    @app.context_processor
    def globals_for_templates():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"], "shop_name": "Boba Bliss"}

    def validate_csrf():
        token = request.form.get("csrf_token", "")
        saved = session.get("csrf_token", "")
        if not saved or not hmac.compare_digest(saved, token):
            abort(400, description="Invalid form token. Refresh the page and try again.")

    @app.before_request
    def protect_post_requests():
        if request.method == "POST":
            validate_csrf()

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "admin_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    def all_drinks(only_available=True):
        query = "SELECT * FROM drinks"
        if only_available:
            query += " WHERE available = 1"
        query += " ORDER BY sort_order, id"
        return get_db().execute(query).fetchall()

    @app.get("/")
    def home():
        return render_template("home.html", featured=all_drinks()[:3])

    @app.get("/menu")
    @app.get("/preview")
    def menu():
        return render_template("menu.html", drinks=all_drinks())

    @app.get("/contact")
    def contact():
        return render_template("contact.html")

    @app.route("/order/<int:drink_id>", methods=["GET", "POST"])
    def order(drink_id):
        drink = get_db().execute("SELECT * FROM drinks WHERE id=? AND available=1", (drink_id,)).fetchone()
        if drink is None:
            abort(404)
        if request.method == "POST":
            name = request.form.get("customer_name", "").strip()
            phone = request.form.get("phone", "").strip()
            size = request.form.get("size", "")
            sweetness = request.form.get("sweetness", "")
            notes = request.form.get("notes", "").strip()
            try:
                qty = int(request.form.get("quantity", "0"))
            except ValueError:
                qty = 0
            if not (2 <= len(name) <= 70 and 7 <= len(phone) <= 25 and
                    size in SIZES and sweetness in SWEETNESS and 1 <= qty <= 10 and
                    len(notes) <= 300):
                flash("Please check your name, phone, size, sweetness, quantity, and notes.", "error")
                return render_template("order.html", drink=drink, sizes=SIZES, sweetness=SWEETNESS), 400
            unit_price = drink["price_cents"] + SIZES[size]
            total = unit_price * qty
            db = get_db()
            cursor = db.execute(
                """INSERT INTO orders
                (customer_name, phone, drink_name, size, sweetness, quantity,
                 price_cents, total_cents, notes, status, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING id""",
                (name, phone, drink["name"], size, sweetness, qty,
                 unit_price, total, notes, "New", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
            )
            new_order_id = cursor.fetchone()["id"]
            db.commit()
            return redirect(url_for("order_success", order_id=new_order_id))
        return render_template("order.html", drink=drink, sizes=SIZES, sweetness=SWEETNESS)

    @app.get("/order-success/<int:order_id>")
    def order_success(order_id):
        # Show only the confirmation number, never personal order data on a public URL.
        # This is a classroom demo, not a payment or POS integration.
        return render_template("success.html", order_id=order_id)

    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        if "admin_id" in session:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = get_db().execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["admin_id"] = user["id"]
                session["admin_username"] = user["username"]
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("dashboard"))
            flash("Incorrect username or password.", "error")
        return render_template("login.html")

    @app.post("/admin/logout")
    @admin_required
    def logout():
        session.clear()
        flash("You have logged out.", "success")
        return redirect(url_for("home"))

    @app.get("/admin")
    @admin_required
    def dashboard():
        db = get_db()
        orders = db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        return render_template("admin.html", drinks=all_drinks(False), orders=orders, statuses=STATUSES)

    def parse_drink():
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        emoji = request.form.get("emoji", "🧋")
        available = 1 if request.form.get("available") == "on" else 0
        try:
            price_cents = round(float(request.form.get("price", "0")) * 100)
            sort_order = int(request.form.get("sort_order", "0"))
        except ValueError:
            return None
        if not (2 <= len(name) <= 80 and len(description) <= 250 and
                50 <= price_cents <= 5000 and emoji in EMOJIS and 0 <= sort_order <= 999):
            return None
        return (name, description, price_cents, emoji, sort_order, available)

    @app.route("/admin/drinks/new", methods=["GET", "POST"])
    @admin_required
    def add_drink():
        if request.method == "POST":
            drink_data = parse_drink()
            if drink_data is None:
                flash("Enter a name, price ($0.50–$50), and valid drink details.", "error")
            else:
                db = get_db()
                db.execute("""INSERT INTO drinks(name,description,price_cents,emoji,sort_order,available)
                    VALUES (?,?,?,?,?,?)""", drink_data)
                db.commit()
                flash("Drink added!", "success")
                return redirect(url_for("dashboard"))
        return render_template("drink_form.html", drink=None, emojis=EMOJIS)

    @app.route("/admin/drinks/<int:drink_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_drink(drink_id):
        db = get_db()
        drink = db.execute("SELECT * FROM drinks WHERE id=?", (drink_id,)).fetchone()
        if not drink:
            abort(404)
        if request.method == "POST":
            drink_data = parse_drink()
            if drink_data is None:
                flash("Enter a name, price ($0.50–$50), and valid drink details.", "error")
            else:
                db.execute("""UPDATE drinks SET name=?,description=?,price_cents=?,emoji=?,
                    sort_order=?,available=? WHERE id=?""", (*drink_data, drink_id))
                db.commit()
                flash("Drink updated!", "success")
                return redirect(url_for("dashboard"))
        return render_template("drink_form.html", drink=drink, emojis=EMOJIS)

    @app.post("/admin/drinks/<int:drink_id>/delete")
    @admin_required
    def delete_drink(drink_id):
        db = get_db()
        db.execute("DELETE FROM drinks WHERE id=?", (drink_id,))
        db.commit()
        flash("Drink deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.post("/admin/orders/<int:order_id>/status")
    @admin_required
    def change_status(order_id):
        status = request.form.get("status", "")
        if status not in STATUSES:
            abort(400)
        db = get_db()
        updated = db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        if updated.rowcount == 0:
            abort(404)
        db.commit()
        flash("Order updated.", "success")
        return redirect(url_for("dashboard") + "#orders")

    with app.app_context():
        init_db()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
