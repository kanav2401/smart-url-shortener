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
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                original_url: original_url,
                custom_code: custom_code || null,
                expires_at: expires_at
                    ? new Date(expires_at).toISOString()
                    : null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            result.textContent =
                data.detail || "Something went wrong.";
            return;
        }

        result.innerHTML = `
            <p>Your shortened URL:</p>

            <a href="${data.short_url}" target="_blank">
                ${data.short_url}
            </a>

            <p>
                Clicks: ${data.clicks}
            </p>

            <p>
                Expires:
                ${
                    data.expires_at
                        ? new Date(data.expires_at).toLocaleString()
                        : "Never"
                }
            </p>

            <button onclick="copyURL('${data.short_url}')">
                Copy URL
            </button>

            <br><br>

            <a href="/analytics/${data.short_code}" target="_blank">
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
            `/api/urls?${params.toString()}`
        );

        const data = await response.json();

        if (!response.ok) {
            return;
        }

        displayURLs(data);
    } catch (error) {
        console.error(error);
    }
}


function displayURLs(data) {
    const container = document.getElementById("url-list");

    if (!container) {
        return;
    }

    if (data.results.length === 0) {
        container.innerHTML = `
            <p class="empty">
                No URLs found.
            </p>
        `;

        updatePagination(data);
        return;
    }

    container.innerHTML = data.results.map(url => `
        <div class="url-item">

            <div class="url-info">

                <strong>
                    <a href="${url.short_url}" target="_blank">
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

                <button onclick="copyURL('${url.short_url}')">
                    Copy
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

        </div>
    `).join("");

    updatePagination(data);
}


function updatePagination(data) {
    const pagination =
        document.getElementById("pagination");

    if (!pagination) {
        return;
    }

    if (data.total_pages <= 1) {
        pagination.innerHTML = "";
        return;
    }

    let buttons = "";

    if (data.page > 1) {
        buttons += `
            <button onclick="loadURLs(${data.page - 1})">
                Previous
            </button>
        `;
    }

    for (
        let page = 1;
        page <= data.total_pages;
        page++
    ) {
        buttons += `
            <button onclick="loadURLs(${page})">
                ${page}
            </button>
        `;
    }

    if (data.page < data.total_pages) {
        buttons += `
            <button onclick="loadURLs(${data.page + 1})">
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
                method: "DELETE"
            }
        );

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
        alert("Unable to connect to the server.");
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


let searchTimeout;


function searchURLs() {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
        loadURLs(1);
    }, 300);
}


window.addEventListener(
    "DOMContentLoaded",
    () => {
        loadURLs();
    }
);