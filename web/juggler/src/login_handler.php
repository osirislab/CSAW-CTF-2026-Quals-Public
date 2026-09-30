<?php
    if (
        !isset($_POST["csrf_token"]) ||
        !hash_equals($_SESSION["csrf_token"], $_POST["csrf_token"])
    ){
        header("Location: /login.php");
        exit();
    }
    $username = $_POST["username"] ?? "";
    $password = $_POST["password"] ?? "";

    $stmt = $pdo->prepare("SELECT id, password, role FROM users WHERE username = ?");
    $stmt->execute([$username]);
    $user = $stmt->fetch();

    if ($user && password_verify($password, $user["password"])){
        $_SESSION = [];
        session_regenerate_id(true);
        $_SESSION["user_id"] = $user["id"];
        $_SESSION["username"] = $username;
        $_SESSION["role"] = $user["role"];
        $_SESSION["csrf_token"] = bin2hex(random_bytes(CSRF_TOKEN_LENGTH));
        header("Location: /dashboard.php");
    }else{
        $_SESSION["error_msg"] = "Invalid username or password";
        header("Location: /login.php");
    }

    exit();
?>