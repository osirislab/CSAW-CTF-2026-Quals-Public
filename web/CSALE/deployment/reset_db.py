import secrets, shutil, sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
from vault import encrypt_password, generate_storage_key

BASE_DIR = Path(__file__).resolve().parent
DB_PATH, PRIVATE_DB_PATH = BASE_DIR / "database.db", BASE_DIR / "private.db"
UPLOAD_DIR, DRAFT_UPLOAD_DIR = BASE_DIR / "static/uploads", BASE_DIR / "draft_uploads"

USERS = [
    ("superdiscreteflaguser", "password123"),
    ("Walter_W", "I-AM_HEISENBURGGER"),
    ("Mr.Krabs", "MONEYYYYYYYYYYYY"),
    ("Gojo", "Can't_touch_thisfrfr"),
    ("Daenerys", "stormborn_targaryan"),
    ("Zoro", "NEEDMOREPAINT"),
    ("OSIRIS", "enjoy_the_ctf_good_luck!"),
    ("Maliketh", "OdeathBecOMEMyBladEONceMOre"),
    ("Zuko", "i-HaVe-REgaINEd_mY_h0NOr!"),
]
LISTINGS = [
    ("Walter_W", "Pizza", "Roof-baked pizza!", 1200, "Walter_Pizza.jpg", None),
    (
        "Daenerys",
        "Dragon eggs",
        "Throwing them into a fire didn't work...",
        1800,
        "Daenerys_Eggs.png",
        None,
    ),
    ("Mr.Krabs", "Sponge", "My sponge named Bob.", 1, "Mr.Krabs_Sponge.png", None),
    ("Gojo", "Worm?", "Found it on some homeless dude.", 500, "Gojo_Worm.png", None),
    (
        "Gojo",
        "Blindfold",
        "LOOKING TO BUY, NOT SELLING!",
        3100,
        "Gojo_Blindfold.png",
        None,
    ),
    (
        "Zoro",
        "Magical tool",
        "I have no idea how this thing works.",
        700,
        "Zoro_Compass.jpg",
        None,
    ),
    ("OSIRIS", "OSIRIS Stickers", "Enjoy the free merch!", 0, "OSIRIS_Logo.png", None),
    (
        "Maliketh",
        "My Black Blade",
        "Need money for deathroot.",
        30000,
        "Maliketh_Blade.png",
        None,
    ),
    (
        "superdiscreteflaguser",
        "Flag",
        "Money will solve your problems!",
        1_000_000_000,
        "Money.png",
        "csawctf{th1s_wAs_EZ}",
    ),
]

SCHEMA = """
CREATE TABLE app_settings(name TEXT PRIMARY KEY,value TEXT);
CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT);
CREATE TABLE login_directory(id INTEGER PRIMARY KEY,display_name TEXT,old_account_number INTEGER);
CREATE TABLE password_notes(id INTEGER PRIMARY KEY,phase INTEGER UNIQUE,key_piece TEXT);
CREATE TABLE password_vault(id INTEGER PRIMARY KEY,user_id INTEGER UNIQUE,encrypted_password TEXT);
CREATE TABLE listings(id INTEGER PRIMARY KEY,owner_id INTEGER,title TEXT,description TEXT,price_cents INTEGER,image_filename TEXT,fulfillment_note TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE account_balances(user_id INTEGER PRIMARY KEY,balance_cents INTEGER DEFAULT 0);
CREATE TABLE cart_items(id INTEGER PRIMARY KEY,user_id INTEGER,listing_id INTEGER,quantity INTEGER DEFAULT 1,UNIQUE(user_id,listing_id));
CREATE TABLE orders(id INTEGER PRIMARY KEY,buyer_id INTEGER,seller_id INTEGER,listing_id INTEGER,title_snapshot TEXT,description_snapshot TEXT,quantity INTEGER,unit_price_cents INTEGER,image_name TEXT,image_bytes BLOB,fulfillment_note TEXT,status TEXT DEFAULT 'Processing',tracking_note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE messages(id INTEGER PRIMARY KEY,sender_id INTEGER,recipient_id INTEGER,listing_id INTEGER,body TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""
PRIVATE_SCHEMA = """
CREATE TABLE seller_release(owner_id INTEGER PRIMARY KEY,password_hash TEXT);
CREATE TABLE draft_listings(id INTEGER PRIMARY KEY,owner_id INTEGER,slug TEXT UNIQUE,title TEXT,description TEXT,price_cents INTEGER,image_filename TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

PRIVATE_LISTINGS = [
    ("Walter_W", "periodic-table", "Periodic Table", "Reserved for Jesse.", 1200, "Walter_Periodic_Table.png"),
    ("Zoro", "black-paint", "Black Paint", "Reserved for Mihawk.", 4100, "Zoro_Paint.png"),
    ("OSIRIS", "receiver-draft", "Receiver draft", "Saved private draft.", 3600, "OSIRIS_Secret.png"),
    ("Zuko", "recovered-photo-proof", "Recovered photo proof", "A private recovery image.", 100, "flag.png"),
]


def reset_db():
    for folder in (UPLOAD_DIR, DRAFT_UPLOAD_DIR):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
    DB_PATH.unlink(missing_ok=True)
    PRIVATE_DB_PATH.unlink(missing_ok=True)
    key, conn = generate_storage_key(), sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO app_settings VALUES('generation',?)", (secrets.token_hex(16),)
    )
    for username, password in USERS:
        user_id = conn.execute(
            "INSERT INTO users(username,password_hash) VALUES(?,?)",
            (username, generate_password_hash(password)),
        ).lastrowid
        conn.execute(
            "INSERT INTO login_directory(display_name,old_account_number) VALUES(?,?)",
            (username, user_id + 7000),
        )
        conn.execute("INSERT INTO account_balances VALUES(?,0)", (user_id,))
        conn.execute(
            "INSERT INTO password_vault(user_id,encrypted_password) VALUES(?,?)",
            (user_id, encrypt_password(password, key)),
        )
    pieces = [key[i : i + 4] for i in range(0, 20, 4)]
    conn.executemany(
        "INSERT INTO password_notes(phase,key_piece) VALUES(?,?)",
        [
            (3, pieces[2]),
            (1, pieces[0]),
            (5, pieces[4]),
            (2, pieces[1]),
            (4, pieces[3]),
        ],
    )
    ids = dict(conn.execute("SELECT username,id FROM users"))
    for owner, title, description, price, image, note in LISTINGS:
        conn.execute(
            "INSERT INTO listings(owner_id,title,description,price_cents,image_filename,fulfillment_note) VALUES(?,?,?,?,?,?)",
            (ids[owner], title, description, price, image, note),
        )
    dragon = conn.execute("SELECT * FROM listings WHERE title='Dragon eggs'").fetchone()
    image = (BASE_DIR / "static/listing_images" / dragon[5]).read_bytes()
    conn.execute(
        "INSERT INTO orders(buyer_id,seller_id,listing_id,title_snapshot,description_snapshot,quantity,unit_price_cents,image_name,image_bytes) VALUES(?,?,?,?,?,1,?,?,?)",
        (
            ids["Walter_W"],
            dragon[1],
            dragon[0],
            dragon[2],
            dragon[3],
            dragon[4],
            dragon[5],
            image,
        ),
    )
    conn.commit()
    conn.close()

    private = sqlite3.connect(PRIVATE_DB_PATH)
    private.executescript(PRIVATE_SCHEMA)
    private.executemany(
        "INSERT INTO seller_release VALUES(?,?)",
        [
            (user_id, generate_password_hash(secrets.token_urlsafe(32)))
            for user_id in ids.values()
        ],
    )
    private.executemany(
        "INSERT INTO draft_listings(owner_id,slug,title,description,price_cents,image_filename) VALUES(?,?,?,?,?,?)",
        [
            (ids[owner], slug, title, description, price, image)
            for owner, slug, title, description, price, image in PRIVATE_LISTINGS
        ],
    )
    private.commit()
    private.close()


if __name__ == "__main__":
    reset_db()
