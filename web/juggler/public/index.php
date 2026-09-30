<?php
    require_once __DIR__ . "/../config/bootstrap.php";
    require_once __DIR__ . "/../src/db.php";
    include __DIR__ . "/../src/templates/header.php"
?>

<?php
    include __DIR__ . "/../src/templates/menu.php"
?>

<section id="about">
    <h2>Can You Juggle?</h2>
    <pre id="ascii-display"></pre>
    <p>
        Captivating the masses with our 1337 juggling skills...
    </p>
</section>

<?php
    include __DIR__ . "/../src/templates/footer.php"
?>

<script src="/js/juggler.js"></script>