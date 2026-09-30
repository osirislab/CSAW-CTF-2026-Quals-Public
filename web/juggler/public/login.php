<?php
    require_once __DIR__ . "/../config/bootstrap.php";
    require_once __DIR__ . "/../src/db.php";

    if ($_SERVER["REQUEST_METHOD"] === "POST")
        require_once __DIR__ . "/../src/login_handler.php";

    include __DIR__ . "/../src/templates/header.php"
?>

<div id="login">
    <h2>Login</h2>
    <div class="form-wrapper">
        <form action="" method="post">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($_SESSION["csrf_token"]) ?>">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
            <button type="submit">Login</button>
        </form>
    </div>
    <p>
        Don't have an account?
        <a href="register.php">Register</a>
    </p>
    <?php if(isset($_SESSION["error_msg"])): ?>
        <p>
            <?php 
                echo htmlspecialchars($_SESSION["error_msg"]);
                unset($_SESSION["error_msg"]);
            ?>
        </p>
    <?php endif; ?>
</div>

<?php include __DIR__ . "/../src/templates/footer.php"?>