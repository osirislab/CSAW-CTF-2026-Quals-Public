<?php
    require_once __DIR__ . "/db.php";

    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT \"user\"
        )"
    );
?>