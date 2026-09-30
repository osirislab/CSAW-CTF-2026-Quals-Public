<?php
    require_once __DIR__ . "/../config/bootstrap.php";
    require_once __DIR__ . "/../src/db.php";

    if ($_SERVER["REQUEST_METHOD"] === "POST")
        require_once __DIR__ . "/../src/register_handler.php";

    include __DIR__ . "/../src/templates/header.php"
?>

<div id="register-user">
    <h2>Register</h2>
    <div class="form-wrapper">
        <form action="" method="post">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($_SESSION["csrf_token"]) ?>">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
            <button type="submit">Register</button>
        </form>
    </div>
    <p>
        Already have an account?
        <a href="login.php">Login</a>
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