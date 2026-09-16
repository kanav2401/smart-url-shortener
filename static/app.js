function getAuthHeaders() {
    const token = localStorage.getItem("access_token");

    if (!token) {
        return {};
    }

    return {
        Authorization: `Bearer ${token}`
    };
}

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");

    window.location.href = "/login";
}

function setupLogout() {
    const logoutButton = document.getElementById("logout-button");

    if (logoutButton) {
        logoutButton.addEventListener("click", logout);
    }
}

function handleUnauthorized(response) {
    if (response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");

        window.location.href = "/login";

        return true;
    }

    return false;
}

async function verifyUser() {
    const token = localStorage.getItem("access_token");

    if (!token) {
        window.location.href = "/login";
        return false;
    }

    try {
        const response = await fetch("/api/auth/me", {
            method: "GET",
            headers: getAuthHeaders()
        });

        if (handleUnauthorized(response)) {
            return false;
        }

        if (!response.ok) {
            console.error("Failed to verify user.");
            return false;
        }

        const user = await response.json();

        localStorage.setItem(
            "user",
            JSON.stringify(user)
        );

        const userName = document.getElementById("user-name");

        if (userName) {
            userName.textContent = user.name;
        }

        return true;
    } catch (error) {
        console.error("Unable to verify user:", error);
        return false;
    }
}

async function shortenURL() {
    const urlInput = document.getElementById("url");
    const customInput = document.getElementById("custom");
    const expirationInput = document.getElementById("expiration");
    const result = document.getElementById("result");

    const original_url = urlInput.value.trim();
    const custom_code = customInput.value.trim();

    const expires_at = expirationInput
        ? expirationInput.value
        : "";

    if (!original_url) {
        result.textContent = "Please enter a URL.";
        return;
    }

    try {
        const response = await fetch("/api/urls", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                original_url: original_url,
                custom_code: custom_code || null,
                expires_at: expires_at
                    ? new Date(expires_at).toISOString()
                    : null
            })
        });

        if (handleUnauthorized(response)) {
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            result.textContent =
                data.detail || "Something went wrong.";
            return;
        }

        result.innerHTML = `
            <p>Your shortened URL:</p>

            <div class="short-url">
                <a
                    href="${data.short_url}"
                    target="_blank"
                >
                    ${data.short_url}
                </a>

                <button
                    class="copy-button"
                    onclick="copyURL('${data.short_url}')"
                >
                    Copy
                </button>
            </div>

            <p>
                Clicks: ${data.clicks}
            </p>

            <p>
                Expires:
                ${
                    data.expires_at
                        ? new Date(
                            data.expires_at
                        ).toLocaleString()
                        : "Never"
                }
            </p>

            <button
                class="qr-button"
                onclick="showQRCode(
                    '${data.short_url}',
                    '${data.short_code}',
                    'new'
                )"
            >
                Show QR Code
            </button>

            <div id="new-qr-container"></div>

            <br>

            <a
                class="analytics-button"
                href="/analytics/${data.short_code}"
                target="_blank"
            >
                View Analytics
            </a>
        `;

        urlInput.value = "";
        customInput.value = "";

        if (expirationInput) {
            expirationInput.value = "";
        }

        loadURLs();
    } catch (error) {
        result.textContent =
            "Unable to connect to the server.";

        console.error(error);
    }
}

async function loadURLs(page = 1) {
    const searchInput = document.getElementById("search");

    const search = searchInput
        ? searchInput.value.trim()
        : "";

    const params = new URLSearchParams({
        page: page,
        limit: 5
    });

    if (search) {
        params.append("search", search);
    }

    try {
        const response = await fetch(
            `/api/urls?${params.toString()}`,
            {
                method: "GET",
                headers: getAuthHeaders()
            }
        );

        if (handleUnauthorized(response)) {
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            console.error(
                data.detail || "Failed to load URLs."
            );
            return;
        }

        displayURLs(data);
    } catch (error) {
        console.error(
            "Error loading URLs:",
            error
        );
    }
}

function displayURLs(data) {
    const container =
        document.getElementById("url-list");

    if (!container) {
        return;
    }

    if (
        !data.results ||
        data.results.length === 0
    ) {
        container.innerHTML = `
            <p class="empty">
                No URLs found.
            </p>
        `;

        updatePagination(data);

        return;
    }

    container.innerHTML = data.results
        .map(url => `
            <div class="url-item">

                <div class="url-info">

                    <strong>
                        <a
                            href="${url.short_url}"
                            target="_blank"
                        >
                            ${url.short_code}
                        </a>
                    </strong>

                    <p>
                        ${url.original_url}
                    </p>

                    <span>
                        Clicks: ${url.clicks}
                    </span>

                    <span>
                        Expires:
                        ${
                            url.expires_at
                                ? new Date(
                                    url.expires_at
                                ).toLocaleString()
                                : "Never"
                        }
                    </span>

                </div>

                <div class="url-actions">

                    <button
                        onclick="copyURL('${url.short_url}')"
                    >
                        Copy
                    </button>

                    <button
                        onclick="showQRCode(
                            '${url.short_url}',
                            '${url.short_code}'
                        )"
                    >
                        QR Code
                    </button>

                    <a
                        href="/analytics/${url.short_code}"
                        target="_blank"
                    >
                        Analytics
                    </a>

                    <button
                        onclick="deleteURL('${url.short_code}')"
                    >
                        Delete
                    </button>

                </div>

                <div
                    id="qr-${url.short_code}"
                    class="qr-container"
                ></div>

            </div>
        `)
        .join("");

    updatePagination(data);
}

function updatePagination(data) {
    const pagination =
        document.getElementById("pagination");

    if (!pagination) {
        return;
    }

    const totalPages =
        data.total_pages || 1;

    const currentPage =
        data.page || 1;

    if (totalPages <= 1) {
        pagination.innerHTML = "";
        return;
    }

    let buttons = "";

    if (currentPage > 1) {
        buttons += `
            <button
                onclick="loadURLs(${currentPage - 1})"
            >
                Previous
            </button>
        `;
    }

    for (
        let page = 1;
        page <= totalPages;
        page++
    ) {
        buttons += `
            <button
                class="${
                    page === currentPage
                        ? "active-page"
                        : ""
                }"
                onclick="loadURLs(${page})"
            >
                ${page}
            </button>
        `;
    }

    if (currentPage < totalPages) {
        buttons += `
            <button
                onclick="loadURLs(${currentPage + 1})"
            >
                Next
            </button>
        `;
    }

    pagination.innerHTML = buttons;
}

async function deleteURL(shortCode) {
    const confirmed = confirm(
        "Are you sure you want to delete this URL?"
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(
            `/api/urls/${shortCode}`,
            {
                method: "DELETE",
                headers: getAuthHeaders()
            }
        );

        if (handleUnauthorized(response)) {
            return;
        }

        const data = await response.json();

        if (!response.ok) {
            alert(
                data.detail ||
                "Failed to delete URL."
            );

            return;
        }

        alert("URL deleted successfully.");

        loadURLs();
    } catch (error) {
        alert(
            "Unable to connect to the server."
        );

        console.error(error);
    }
}

function copyURL(url) {
    navigator.clipboard
        .writeText(url)
        .then(() => {
            alert("URL copied!");
        })
        .catch(() => {
            alert("Failed to copy URL.");
        });
}

function showQRCode(
    shortUrl,
    shortCode,
    location = null
) {
    let container;

    if (location === "new") {
        container =
            document.getElementById(
                "new-qr-container"
            );
    } else {
        container =
            document.getElementById(
                `qr-${shortCode}`
            );
    }

    if (!container) {
        return;
    }

    if (
        container.innerHTML.trim() !== ""
    ) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = `
        <div class="qr-box">

            <h3>
                QR Code
            </h3>

            <img
                src="/api/qr/${shortCode}"
                alt="QR Code"
                class="qr-image"
            >

            <p>
                Scan this QR code to open your
                shortened URL.
            </p>

            <a
                href="/api/qr/${shortCode}"
                download="smart-url-qr-code.png"
                class="download-qr-button"
            >
                Download QR Code
            </a>

        </div>
    `;
}

let searchTimeout;

function searchURLs() {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
        loadURLs(1);
    }, 300);
}

window.logout = logout;
window.shortenURL = shortenURL;
window.loadURLs = loadURLs;
window.deleteURL = deleteURL;
window.copyURL = copyURL;
window.showQRCode = showQRCode;
window.searchURLs = searchURLs;

window.addEventListener(
    "DOMContentLoaded",
    async () => {
        setupLogout();

        const authenticated =
            await verifyUser();

        if (!authenticated) {
            return;
        }

        loadURLs();
    }
);