const registerForm =
    document.getElementById("register-form");

const message =
    document.getElementById("register-message");


registerForm.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const name =
            document.getElementById("name")
                .value
                .trim();

        const email =
            document.getElementById("email")
                .value
                .trim();

        const password =
            document.getElementById("password")
                .value;

        const confirmPassword =
            document.getElementById("confirm-password")
                .value;


        if (password !== confirmPassword) {

            message.textContent =
                "Passwords do not match.";

            return;
        }


        if (password.length < 6) {

            message.textContent =
                "Password must be at least 6 characters long.";

            return;
        }


        message.textContent =
            "Creating account...";


        try {

            const response = await fetch(
                "/api/auth/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        name,
                        email,
                        password
                    })
                }
            );


            const data = await response.json();


            if (!response.ok) {

                message.textContent =
                    data.detail ||
                    "Registration failed.";

                return;
            }


            message.textContent =
                "Account created successfully. Redirecting to login...";


            setTimeout(() => {

                window.location.href = "/login";

            }, 1000);


        } catch (error) {

            message.textContent =
                "Unable to connect to the server.";

            console.error(error);
        }

    }
);