const loginForm = document.getElementById("login-form");
const message = document.getElementById("login-message");


loginForm.addEventListener("submit", async (event) => {

    event.preventDefault();

    const email =
        document.getElementById("email").value.trim();

    const password =
        document.getElementById("password").value;


    message.textContent = "Logging in...";


    try {

        const response = await fetch(
            "/api/auth/login",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email,
                    password
                })
            }
        );


        const data = await response.json();


        if (!response.ok) {

            message.textContent =
                data.detail || "Login failed.";

            return;
        }


        localStorage.setItem(
            "access_token",
            data.access_token
        );


        localStorage.setItem(
            "user",
            JSON.stringify(data.user)
        );


        window.location.href = "/";

    } catch (error) {

        message.textContent =
            "Unable to connect to the server.";

        console.error(error);
    }

});