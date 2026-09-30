<?php
    define("CSRF_TOKEN_LENGTH", 32);

    session_set_cookie_params([
        "httponly" => true,
        "secure" => !empty($_SERVER["HTTPS"]),
        "samesite" => "Lax"
    ]);

    if (session_status() === PHP_SESSION_NONE)
        session_start();

    if (!isset($_SESSION["csrf_token"]))
        $_SESSION["csrf_token"] = bin2hex(random_bytes(CSRF_TOKEN_LENGTH));
?>