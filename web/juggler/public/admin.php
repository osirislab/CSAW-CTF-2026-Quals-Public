<?php
    require_once __DIR__ . "/../config/bootstrap.php";
    require_once __DIR__ ."/../src/db.php";

    $config = parse_ini_file(__DIR__ . "/../config/config.ini", true);
    $adminRoles = $config["Roles"]["admin_roles"];

    if (!isset($_SESSION["role"]) || 
        !in_array($_SESSION["role"], $adminRoles)
    ){
        header("Location: index.php");
        exit();
    }

    include __DIR__ . "/../src/templates/header.php";
?>

<section id="admin-panel">
    <h2>Welcome, Admin</h2>
    <div><?php echo file_get_contents("../flag.txt"); ?></div>
</section>

<?php include __DIR__ . "/../src/templates/footer.php"?>