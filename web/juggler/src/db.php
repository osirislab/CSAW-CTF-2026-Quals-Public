<?php
    $DB_FILE = __DIR__ . "/../challenge.db";

    try{
        $pdo = new PDO("sqlite:$DB_FILE");
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    }catch(PDOException $e){
        die("Failed to connect to db: " . $e->getMessage());
    }
?>