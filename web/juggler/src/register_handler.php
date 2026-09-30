<?php
    if (
        !isset($_POST["csrf_token"]) ||
        !hash_equals($_SESSION["csrf_token"], $_POST["csrf_token"])
    ){
        header("Location: /register.php");
        exit();
    }

    $username = trim($_POST["username"] ?? "");
    $password = trim($_POST["password"] ?? "");
    if ($username === "" || $password === ""){
        $_SESSION["error_msg"] = "Username and password are required";
        header("Location: /register.php");
        exit();
    }
    $password = password_hash($password, PASSWORD_DEFAULT);

    $stmt = $pdo->prepare("SELECT 1 FROM USERS WHERE username = ? LIMIT 1");
    $stmt->execute([$username]);
    $userExists = (bool)$stmt->fetchColumn();
    if ($userExists){
        $_SESSION["error_msg"] = "Username already taken";
        header("Location: /register.php");
        exit();
    }
    
    try{
        $stmt = $pdo->prepare("INSERT INTO users (username, password) VALUES (?, ?)");
        $stmt->execute([$username, $password]);
        $_SESSION["error_msg"] = "Registration successful";
    }catch(PDOException $e){
        $_SESSION["error_msg"] = "Unknown error occurred";
    }

    header("Location: /register.php");
    exit();
?>