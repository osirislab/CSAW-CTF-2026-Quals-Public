<?php
    require_once __DIR__ . "/../config/bootstrap.php";
    require_once __DIR__ . "/../src/db.php";

    if (!isset($_SESSION["user_id"])){
        header("Location: login.php");
        exit();
    }

    $contentType = $_SERVER["CONTENT_TYPE"] ?? "";
    if ($_SERVER["REQUEST_METHOD"] === "POST"
        && $contentType === "application/json"
    )
        require_once __DIR__ . "/../src/profile_update.php";

    if ($_SERVER["REQUEST_METHOD"] === "POST" && $_POST["action"] === "logout")
        require_once __DIR__ . "/../src/logout_handler.php";

    include __DIR__ .  "/../src/templates/header.php"
?>

<section id="dashboard">
    <h2>Dashboard</h2>
    <p>Welcome, <span id="display-username"><?php echo htmlspecialchars($_SESSION["username"]) ?></span></p>
    <div class="toggle-wrapper">
        <button onclick="toggleProfileForm()">Edit Profile</button>
    </div>
    <div id="update-profile-form-wrapper" class="form-wrapper hidden"><br>
        <form action="" method="post"><br>
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($_SESSION["csrf_token"]) ?>">
            <input type="hidden" name="action" value="update_profile">
            <label for="username">New username:</label>
            <input type="text" id="username" name="username">
            <label for="password">New password:</label>
            <input type="password" id="password" name="password">
            <button type="submit">Save Changes</button>
            <button type="button" class="cancel-text" onclick="toggleProfileForm()">Cancel</button>
        </form>
    </div>
    <div id="logout-form-wrapper" class=form-wrapper>
        <form action="" method="post">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($_SESSION["csrf_token"]) ?>">
            <input type="hidden" name="action" value="logout">
            <button type="submit">Logout</button>
        </form>
    </div>
    <div id="status-message"></div>
</section>

<script src="/js/profile.js"></script>
<?php include __DIR__ . "/../src/templates/footer.php"?>