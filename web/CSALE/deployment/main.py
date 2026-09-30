import io, os, re, secrets, sqlite3
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from flask import (Flask,Response,abort,redirect,render_template,request,send_file,session,)
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash
from vault import encrypt_password

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CSALE_DB_PATH", ROOT / "database.db"))
PRIVATE_DB_PATH = Path(os.environ.get("CSALE_PRIVATE_DB_PATH", ROOT / "private.db"))
LISTING_IMAGE_DIR = ROOT / "static/listing_images"
PRIVATE_LISTING_IMAGE_DIR = ROOT / "private_listing_images"
UPLOAD_DIR = Path(os.environ.get("CSALE_UPLOAD_DIR", ROOT / "static/uploads"))
DRAFT_UPLOAD_DIR = Path(os.environ.get("CSALE_DRAFT_UPLOAD_DIR", ROOT / "draft_uploads"))
FLAG_IMAGE_PATH = Path(os.environ.get("FLAG_IMAGE_PATH", PRIVATE_LISTING_IMAGE_DIR / "flag.png"))
OSRS_PUBLIC_KEY_PATH = ROOT / "osrs_public.pem"
MAX_DESCRIPTION_BYTES = 446


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

def normalize_png(image_bytes):
    try:
        with Image.open(io.BytesIO(image_bytes)) as picture:
            output = io.BytesIO()
            picture.convert("RGBA").save(output, "PNG", compress_level=9)
            return output.getvalue()
    except (OSError, ValueError) as error:
        raise ValueError("Invalid image.") from error

#what happens in CSALE stays in CSALE...
def encrypt_description(description, public_key_path):
    public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
    return public_key.encrypt(
        description,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def return_one(sql, values=(), path=None):
    conn = connect(path)
    result = conn.execute(sql, values).fetchone()
    conn.close()

    return result
def current_user_id():
    user_id = session.get("user_id")
    generation = return_one("SELECT value FROM app_settings WHERE name='generation'")
    if user_id and generation and session.get("generation") == generation["value"]:
        return user_id
    session.clear()


def current_user():
    user_id = current_user_id()
    return (
        return_one("SELECT id,username FROM users WHERE id=?", (user_id,)) if user_id else None
    )

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        return view(*args, **kwargs) if current_user_id() else redirect("/login")
    return wrapped


@app.context_processor
def template_globals():
    return {"current_user": current_user()}


def start_session(user_id):
    session.clear()
    session.update(
        user_id=user_id,
        generation=return_one("SELECT value FROM app_settings WHERE name='generation'")[
            "value"
        ],
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user_id():
        return redirect("/")
    error = None
    if request.method == "POST":
        username, password = request.form.get("username", ""), request.form.get(
            "password", ""
        )
        cleaned = re.sub(r"[^A-Za-z0-9.]", "", username)[:32]
        conn = connect()
        conn.execute(
            f"SELECT old_account_number FROM login_directory WHERE display_name='{cleaned}'"
        ).fetchone()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            start_session(user["id"])
            return redirect("/")
        error = "The username or password was not accepted."
    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", error=None)
    username, password = request.form.get("username", "").strip(), request.form.get(
        "password", ""
    )
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        return (
            render_template(
                "signup.html",
                error="Use 3-32 letters, numbers, dots, dashes, or underscores.",
            ),
            400,
        )
    if not password:
        return render_template("signup.html", error="Password is required."), 400
    conn, private = connect(), connect(PRIVATE_DB_PATH)
    try:
        key = "".join(
            row[0]
            for row in conn.execute(
                "SELECT key_piece FROM password_notes ORDER BY phase"
            )
        )
        user_id = conn.execute(
            "INSERT INTO users(username,password_hash) VALUES(?,?)",
            (username, generate_password_hash(password)),
        ).lastrowid
        conn.execute("INSERT INTO account_balances VALUES(?,0)", (user_id,))
        conn.execute(
            "INSERT INTO login_directory(display_name,old_account_number) VALUES(?,?)",
            (username, user_id + 7000),
        )
        conn.execute(
            "INSERT INTO password_vault(user_id,encrypted_password) VALUES(?,?)",
            (user_id, encrypt_password(password, key)),
        )
        private.execute(
            "INSERT INTO seller_release VALUES(?,?)",
            (user_id, generate_password_hash(secrets.token_urlsafe(32))),
        )
        conn.commit()
        private.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        private.rollback()
        return render_template("signup.html", error="That username is taken."), 400
    finally:
        conn.close()
        private.close()
    start_session(user_id)
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
@login_required
def home():
    query = request.args.get("q", "")
    base = "SELECT l.id,l.title,l.description,l.price_cents,l.image_filename,u.username owner,'' created_at FROM listings l JOIN users u ON u.id=l.owner_id"
    conn, error = connect(), None
    try:
        sql = (
            base
            + (
                " WHERE ((l.title||' '||l.description||' '||u.username) LIKE '%"
                + query
                + "%')"
                if query
                else ""
            )
            + " ORDER BY l.id DESC"
        )
        listings = conn.execute(sql).fetchall()
    except sqlite3.Error:
        listings, error = [], "Search failed."
    balance = conn.execute(
        "SELECT balance_cents FROM account_balances WHERE user_id=?",
        (current_user_id(),),
    ).fetchone()[0]
    count = conn.execute(
        "SELECT COALESCE(SUM(quantity),0) FROM cart_items WHERE user_id=?",
        (current_user_id(),),
    ).fetchone()[0]
    conn.close()
    return render_template(
        "home.html",
        listings=listings,
        query=query,
        error=error,
        balance=balance,
        cart_count=count,
    )


def get_listing(listing_id):
    return return_one(
        "SELECT l.*,u.username owner FROM listings l JOIN users u ON u.id=l.owner_id WHERE l.id=?",
        (listing_id,),
    )


def image_path(filename, folders):
    if filename and Path(filename).name == filename:
        for folder in folders:
            path = folder / filename
            if path.is_file():
                return path


@app.route("/listings/<int:listing_id>")
@login_required
def listing(listing_id):
    item = get_listing(listing_id)
    return render_template("listing.html", listing=item) if item else abort(404)


@app.route("/listings/<int:listing_id>/image")
@login_required
def listing_image(listing_id):
    item = get_listing(listing_id)
    path = (
        image_path(item["image_filename"], (UPLOAD_DIR, LISTING_IMAGE_DIR))
        if item
        else None
    )
    return send_file(path) if path else abort(404)


def html_frame(fragment):
    response = Response(
        f"<!doctype html><style>html,body{{background:#101014;color:#d4d4d8}}body{{padding:12px;font:15px system-ui}}</style>{fragment}",
        content_type="text/html",
    )
    response.headers["Content-Security-Policy"] = (
        "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; form-action 'none'"
    )
    return response


@app.route("/listings/<int:listing_id>/description-frame")
@login_required
def description_frame(listing_id):
    item = get_listing(listing_id)
    return html_frame(item["description"]) if item else abort(404)


def save_image(upload, folder):
    if not upload or Path(upload.filename or "").suffix.lower() not in {
        ".png",
        ".jpg",
        ".jpeg",
    }:
        raise ValueError("Choose a PNG or JPG image.")
    data = normalize_png(upload.read())
    folder.mkdir(parents=True, exist_ok=True)
    name = secrets.token_hex(12) + ".png"
    (folder / name).write_bytes(data)
    return name


@app.route("/listings/new")
@login_required
def new_listing():
    return render_template("new_listing.html", error=None)


@app.route("/listings", methods=["POST"])
@login_required
def create_listing():
    title, description = request.form.get("title", "").strip(), request.form.get(
        "description", ""
    )
    try:
        price = Decimal(request.form.get("price", ""))
        if (
            not title
            or not description
            or len(description.encode("utf-8")) > MAX_DESCRIPTION_BYTES
            or not 0 <= price <= 10_000_000
        ):
            raise ValueError
        image = save_image(request.files.get("attachment"), UPLOAD_DIR)
    except (InvalidOperation, ValueError) as error:
        return (
            render_template("new_listing.html", error=str(error) or "Invalid listing."),
            400,
        )
    conn = connect()
    listing_id = conn.execute(
        "INSERT INTO listings(owner_id,title,description,price_cents,image_filename) VALUES(?,?,?,?,?)",
        (current_user_id(), title, description, int(price * 100), image),
    ).lastrowid
    conn.commit()
    conn.close()
    return redirect(f"/listings/{listing_id}")


def get_draft(slug):
    draft = return_one("SELECT * FROM draft_listings WHERE slug=?", (slug,), PRIVATE_DB_PATH)
    if not draft:
        return None
    result = dict(draft)
    result["owner"] = return_one(
        "SELECT username FROM users WHERE id=?", (draft["owner_id"],)
    )["username"]
    return result


def draft_file(draft):
    return image_path(
        Path(draft["image_filename"]).name,
        (DRAFT_UPLOAD_DIR, PRIVATE_LISTING_IMAGE_DIR),
    )


@app.route("/account/drafts")
@login_required
def drafts():
    conn = connect(PRIVATE_DB_PATH)
    items = conn.execute(
        "SELECT * FROM draft_listings WHERE owner_id=? ORDER BY id DESC",
        (current_user_id(),),
    ).fetchall()
    conn.close()
    return render_template("drafts.html", drafts=items)


@app.route("/<slug>/unlock", methods=["GET", "POST"])
@login_required
def draft_unlock(slug):
    draft = get_draft(slug)
    if not draft:
        abort(404)
    owner, error = draft["owner_id"] == current_user_id(), None
    if request.method == "POST":
        if not owner:
            abort(403)
        release = return_one(
            "SELECT password_hash FROM seller_release WHERE owner_id=?",
            (current_user_id(),),
            PRIVATE_DB_PATH,
        )
        if not release or not check_password_hash(
            release["password_hash"], request.form.get("release_password", "")
        ):
            error = "Wrong release password."
        else:
            data, name = (
                normalize_png(draft_file(draft).read_bytes()),
                secrets.token_hex(12) + ".png",
            )
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            (UPLOAD_DIR / name).write_bytes(data)
            conn, private = connect(), connect(PRIVATE_DB_PATH)
            listing_id = conn.execute(
                "INSERT INTO listings(owner_id,title,description,price_cents,image_filename) VALUES(?,?,?,?,?)",
                (
                    draft["owner_id"],
                    draft["title"],
                    draft["description"],
                    draft["price_cents"],
                    name,
                ),
            ).lastrowid
            private.execute("DELETE FROM draft_listings WHERE id=?", (draft["id"],))
            conn.commit()
            private.commit()
            conn.close()
            private.close()
            return redirect(f"/listings/{listing_id}")
    return render_template(
        "draft_unlock.html", draft=draft, is_owner=owner, error=error
    )


@app.route("/<slug>/preview")
@login_required
def draft_preview(slug):
    draft = get_draft(slug)
    path = draft_file(draft) if draft else None
    return send_file(path) if path else abort(404)


def signed_32(value):
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


@app.route("/cart")
@login_required
def cart():
    conn = connect()
    items = conn.execute(
        "SELECT c.id,c.quantity,l.id listing_id,l.title,l.price_cents,u.username seller FROM cart_items c JOIN listings l ON l.id=c.listing_id JOIN users u ON u.id=l.owner_id WHERE c.user_id=?",
        (current_user_id(),),
    ).fetchall()
    balance = conn.execute(
        "SELECT balance_cents FROM account_balances WHERE user_id=?",
        (current_user_id(),),
    ).fetchone()[0]
    conn.close()
    total = sum(x["price_cents"] * x["quantity"] for x in items)
    errors = {
        "empty": "Your cart is empty.",
        "funds": "You don't have enough money.",
        "own": "You cannot buy your own listing.",
        "bad": "Checkout failed.",
    }
    return render_template(
        "cart.html",
        items=items,
        balance=balance,
        total=total,
        cart_count=sum(x["quantity"] for x in items),
        error=errors.get(request.args.get("error")),
    )


@app.route("/cart/items", methods=["POST"])
@login_required
def add_to_cart():
    try:
        listing_id = int(request.form.get("listing_id", ""))
        quantity = max(1, min(25, int(request.form.get("quantity", 1))))
    except ValueError:
        abort(400)
    item = get_listing(listing_id)
    if not item:
        abort(404)
    if item["owner_id"] == current_user_id():
        abort(403)
    conn = connect()
    conn.execute(
        "INSERT INTO cart_items(user_id,listing_id,quantity) VALUES(?,?,?) ON CONFLICT(user_id,listing_id) DO UPDATE SET quantity=MIN(25,quantity+excluded.quantity)",
        (current_user_id(), listing_id, quantity),
    )
    conn.commit()
    conn.close()
    return redirect("/cart")


@app.route("/cart/items/<int:item_id>/remove", methods=["POST"])
@login_required
def remove_cart_item(item_id):
    conn = connect()
    conn.execute(
        "DELETE FROM cart_items WHERE id=? AND user_id=?", (item_id, current_user_id())
    )
    conn.commit()
    conn.close()
    return redirect("/cart")


@app.route("/cart/checkout", methods=["POST"])
@login_required
def checkout():
    user_id = current_user_id()
    conn = connect()
    try:
        items = conn.execute(
            "SELECT c.quantity,l.* FROM cart_items c JOIN listings l ON l.id=c.listing_id WHERE c.user_id=?",
            (user_id,),
        ).fetchall()
        if not items:
            return redirect("/cart?error=empty")
        if any(x["owner_id"] == user_id for x in items):
            return redirect("/cart?error=own")
        total = signed_32(sum(x["price_cents"] * x["quantity"] for x in items))
        balance = conn.execute(
            "SELECT balance_cents FROM account_balances WHERE user_id=?",
            (user_id,),
        ).fetchone()[0]
        if total > balance or balance - total < 0:
            return redirect("/cart?error=funds")
        for item in items:
            path = image_path(item["image_filename"], (UPLOAD_DIR, LISTING_IMAGE_DIR))
            image = normalize_png(path.read_bytes())
            conn.execute(
                "INSERT INTO orders(buyer_id,seller_id,listing_id,title_snapshot,description_snapshot,quantity,unit_price_cents,image_name,image_bytes,fulfillment_note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    item["owner_id"],
                    item["id"],
                    item["title"],
                    item["description"],
                    item["quantity"],
                    item["price_cents"],
                    item["image_filename"],
                    image,
                    item["fulfillment_note"],
                ),
            )
        conn.execute(
            "UPDATE account_balances SET balance_cents=? WHERE user_id=?",
            (balance - total, user_id),
        )
        conn.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
        conn.commit()
    except (sqlite3.Error, ValueError, OSError):
        conn.rollback()
        if app.testing:
            raise
        return redirect("/cart?error=bad")
    finally:
        conn.close()
    return redirect("/account/orders")


def get_order(order_id):
    return return_one(
        "SELECT o.*,b.username buyer,s.username seller FROM orders o JOIN users b ON b.id=o.buyer_id JOIN users s ON s.id=o.seller_id WHERE o.id=?",
        (order_id,),
    )


@app.route("/account/orders")
@login_required
def orders():
    conn = connect()
    items = conn.execute(
        "SELECT o.*,u.username seller FROM orders o JOIN users u ON u.id=o.seller_id WHERE buyer_id=? ORDER BY o.id DESC",
        (current_user_id(),),
    ).fetchall()
    conn.close()
    return render_template("orders.html", orders=items)


@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = get_order(order_id)
    return render_template("order_detail.html", order=order) if order else abort(404)


@app.route("/orders/<int:order_id>/image")
@login_required
def order_image(order_id):
    order = get_order(order_id)
    return (
        send_file(io.BytesIO(order["image_bytes"]), mimetype="image/png")
        if order
        else abort(404)
    )


@app.route("/orders/<int:order_id>/export.osrs", methods=["POST"])
@login_required
def export_order(order_id):
    order = get_order(order_id)
    if not order:
        abort(404)
    try:
        record = encrypt_description(
            order["description_snapshot"].encode("utf-8"),
            OSRS_PUBLIC_KEY_PATH,
        )
    except (ValueError, OSError, UnicodeError):
        return redirect(f"/orders/{order_id}?error=export")
    return send_file(
        io.BytesIO(record), as_attachment=True, download_name=f"order-{order_id}.osrs"
    )


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    conn, error = connect(), None
    if request.method == "POST":
        recipient = conn.execute(
            "SELECT id FROM users WHERE username=?",
            (request.form.get("recipient_username", ""),),
        ).fetchone()
        body = request.form.get("body", "")
        if not recipient or not body:
            error = "Recipient and message are required."
        else:
            conn.execute(
                "INSERT INTO messages(sender_id,recipient_id,body) VALUES(?,?,?)",
                (current_user_id(), recipient["id"], body[:4096]),
            )
            conn.commit()
            conn.close()
            return redirect("/messages")
    items = conn.execute(
        "SELECT m.*,s.username sender,r.username recipient FROM messages m JOIN users s ON s.id=m.sender_id JOIN users r ON r.id=m.recipient_id WHERE sender_id=? OR recipient_id=? ORDER BY m.id DESC",
        (current_user_id(), current_user_id()),
    ).fetchall()
    conn.close()
    return render_template("messages.html", messages=items, error=error)


@app.route("/messages/<int:message_id>/body-frame")
@login_required
def message_frame(message_id):
    message = return_one(
        "SELECT body FROM messages WHERE id=? AND (sender_id=? OR recipient_id=?)",
        (message_id, current_user_id(), current_user_id()),
    )
    return html_frame(message["body"]) if message else abort(404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
