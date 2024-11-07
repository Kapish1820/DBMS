document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("signupForm");
    form.addEventListener("submit", function(event) {
        event.preventDefault();
        window.location.href = "user_login.html";
    });
});