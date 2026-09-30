document.querySelector("#update-profile-form-wrapper form").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const newUserName = document.querySelector("#username").value;
    const statusMsg = document.querySelector("#status-message");

    const res = await fetch("/dashboard.php", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            username: document.querySelector("#username").value,
            password: document.querySelector("#password").value,
            csrf_token: document.querySelector("[name='csrf_token']").value
        })
    });

    const data = await res.json();

    if (res.ok && data.status === "success"){
        /* Dynamically update username display */
        document.querySelector("#display-username").textContent = newUserName;
        statusMsg.textContent = "Profile updated";
        document.querySelector("#username").value = "";
        document.querySelector("#password").value = "";
    }else{
        statusMsg.textContent = `Failed to update profile: ${data.message}`;
    }
})


let toggleProfileForm = () => {
    const form = document.querySelector(`#update-profile-form-wrapper`);
    form.classList.toggle('hidden');
}


window.addEventListener('click', function(event) {
    const modal = document.getElementById('update-profile-form-wrapper');
    if (event.target === modal) {
        modal.classList.add('hidden');
    }
});