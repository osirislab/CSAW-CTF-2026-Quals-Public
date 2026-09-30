<?php
    // Receive JSON update data
    $jsonData = json_decode(file_get_contents("php://input"), true);
    if (!$jsonData){
        http_response_code(400);
        echo json_encode(["status" => "failed", "message" => "Malformed input"]);
        exit();
    }

    if (!isset($jsonData["csrf_token"]) ||
        !hash_equals($_SESSION["csrf_token"], $jsonData["csrf_token"])
    ){
        http_response_code(403);
        echo json_encode(["status" => "failed", "message" => "Invalid CSRF token"]);
        exit();
    }

    if (!isset($jsonData["username"]) || trim($jsonData["username"]) === ""){
        http_response_code(400);
        echo json_encode(["status" => "failed", "message" => "Username cannot be empty"]);
        exit();
    }

    $stmt = $pdo->prepare("SELECT id FROM users WHERE username = ? AND id != ?");
    $stmt->execute([$jsonData["username"], $_SESSION["user_id"]]);
    if ($stmt->fetch()){
        http_response_code(418);
        echo json_encode(["status" => "failed", "message" => "Username already exists"]);
        exit();
    }

    $table = "users";
    $stmt = $pdo->query("PRAGMA table_info($table)");
    $columns = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $dbColumns = array_column($columns, "name");

    // Update session and DB
    foreach($jsonData as $jsonKey => $jsonValue){
        if (array_key_exists($jsonKey, $_SESSION))
            $_SESSION[$jsonKey] = $jsonValue;
        if (in_array($jsonKey, $dbColumns, true)){
            $stmt = $pdo->prepare("UPDATE users SET `$jsonKey` = ? WHERE id = ?");
            if ($jsonKey === "password")
                $jsonValue = password_hash($jsonValue, PASSWORD_DEFAULT);
            $stmt->execute([$jsonValue, $_SESSION["user_id"]]);
        }
    }

    http_response_code(200);
    echo json_encode(["status" => "success"]);
    exit();
?>