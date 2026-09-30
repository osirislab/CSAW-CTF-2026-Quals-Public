<?php
    if (
        !isset($_POST["csrf_token"]) ||
        !hash_equals($_SESSION["csrf_token"], $_POST["csrf_token"])
    ){
        header("Location: /index.php");
        exit();
    }

    $params = session_get_cookie_params();
    setcookie(
        session_name(),
        "",
        time() - 1,
        $params["path"],
        $params["domain"],
        $params["secure"],
        $params["httponly"]
    );

    session_destroy();
    header("Location: index.php");
    exit();
?>