async function shortenURL() {
    const urlInput = document.getElementById("url");
    const customInput = document.getElementById("custom");
    const result = document.getElementById("result");

    const original_url = urlInput.value.trim();
    const custom_code = customInput.value.trim();

    if (!original_url) {
        result.textContent = "Please enter a URL.";
        return;
    }

    result.textContent = "Creating short URL...";

    try {
        const response = await fetch("/api/urls", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                original_url: original_url,
                custom_code: custom_code || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            result.textContent = data.detail || "Something went wrong.";
            return;
        }

        result.innerHTML = `
            <p>Your shortened URL:</p>

            <div class="short-url">
                <a href="${data.short_url}" target="_blank">
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
                Clicks: <strong>${data.clicks}</strong>
            </p>

            <button
                class="analytics-button"
                onclick="loadAnalytics('${data.short_code}')"
            >
                View Analytics
            </button>
        `;

        await loadAnalytics(data.short_code);
        await loadURLs();

    } catch (error) {
        result.textContent = "Unable to connect to the server.";
    }
}


async function loadAnalytics(shortCode) {
    const analyticsContent = document.getElementById("analyticsContent");

    analyticsContent.innerHTML = `
        <p>Loading analytics...</p>
    `;

    try {
        const response = await fetch(
            `/api/urls/${shortCode}/analytics`
        );

        const data = await response.json();

        if (!response.ok) {
            analyticsContent.innerHTML = `
                <p class="error">
                    ${data.detail || "Unable to load analytics."}
                </p>
            `;
            return;
        }

        let clickHistory = "";

        if (data.clicks.length === 0) {
            clickHistory = `
                <p class="no-clicks">
                    No clicks recorded yet.
                </p>
            `;
        } else {
            clickHistory = `
                <div class="click-table-container">
                    <table class="click-table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>IP Address</th>
                                <th>Referrer</th>
                                <th>User Agent</th>
                            </tr>
                        </thead>

                        <tbody>
                            ${data.clicks.map(click => `
                                <tr>
                                    <td>
                                        ${formatDate(click.clicked_at)}
                                    </td>

                                    <td>
                                        ${click.ip_address || "Unknown"}
                                    </td>

                                    <td>
                                        ${click.referrer || "Direct"}
                                    </td>

                                    <td class="user-agent">
                                        ${click.user_agent || "Unknown"}
                                    </td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            `;
        }

        analyticsContent.innerHTML = `
            <div class="analytics-summary">

                <div class="stat">
                    <span class="stat-label">Short Code</span>
                    <strong>${data.short_code}</strong>
                </div>

                <div class="stat">
                    <span class="stat-label">Total Clicks</span>
                    <strong>${data.total_clicks}</strong>
                </div>

                <div class="stat">
                    <span class="stat-label">Created</span>
                    <strong>${formatDate(data.created_at)}</strong>
                </div>

                <div class="stat">
                    <span class="stat-label">Expires</span>
                    <strong>
                        ${data.expires_at
                            ? formatDate(data.expires_at)
                            : "Never"}
                    </strong>
                </div>

            </div>

            <div class="original-url">
                <span class="stat-label">Original URL</span>

                <a
                    href="${data.original_url}"
                    target="_blank"
                >
                    ${data.original_url}
                </a>
            </div>

            <h3>Click History</h3>

            ${clickHistory}
        `;

    } catch (error) {
        analyticsContent.innerHTML = `
            <p class="error">
                Unable to connect to the server.
            </p>
        `;
    }
}


async function loadURLs() {
    const urlsContent = document.getElementById("urlsContent");

    urlsContent.innerHTML = `
        <p>Loading URLs...</p>
    `;

    try {
        const response = await fetch("/api/urls");

        const data = await response.json();

        if (!response.ok) {
            urlsContent.innerHTML = `
                <p class="error">
                    ${data.detail || "Unable to load URLs."}
                </p>
            `;
            return;
        }

        if (data.length === 0) {
            urlsContent.innerHTML = `
                <p class="no-clicks">
                    You haven't created any shortened URLs yet.
                </p>
            `;
            return;
        }

        urlsContent.innerHTML = `
            <div class="urls-table-container">

                <table class="urls-table">

                    <thead>
                        <tr>
                            <th>Short URL</th>
                            <th>Original URL</th>
                            <th>Clicks</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>

                    <tbody>

                        ${data.map(url => `
                            <tr>

                                <td>
                                    <a
                                        href="${url.short_url}"
                                        target="_blank"
                                        class="short-link"
                                    >
                                        /${url.short_code}
                                    </a>
                                </td>

                                <td class="original-cell">
                                    <a
                                        href="${url.original_url}"
                                        target="_blank"
                                    >
                                        ${url.original_url}
                                    </a>
                                </td>

                                <td>
                                    <strong>${url.clicks}</strong>
                                </td>

                                <td>
                                    ${formatDate(url.created_at)}
                                </td>

                                <td>

                                    <div class="actions">

                                        <button
                                            class="action-button"
                                            onclick="copyURL('${url.short_url}')"
                                        >
                                            Copy
                                        </button>

                                        <button
                                            class="action-button"
                                            onclick="loadAnalytics('${url.short_code}')"
                                        >
                                            Analytics
                                        </button>

                                        <button
                                            class="action-button delete-button"
                                            onclick="deleteURL('${url.short_code}')"
                                        >
                                            Delete
                                        </button>

                                    </div>

                                </td>

                            </tr>
                        `).join("")}

                    </tbody>

                </table>

            </div>
        `;

    } catch (error) {
        urlsContent.innerHTML = `
            <p class="error">
                Unable to connect to the server.
            </p>
        `;
    }
}


async function deleteURL(shortCode) {
    const confirmed = confirm(
        `Are you sure you want to delete /${shortCode}?`
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
            alert(data.detail || "Unable to delete URL.");
            return;
        }

        await loadURLs();

        const analyticsContent =
            document.getElementById("analyticsContent");

        analyticsContent.innerHTML = `
            <p class="no-clicks">
                URL deleted successfully.
            </p>
        `;

    } catch (error) {
        alert("Unable to connect to the server.");
    }
}


function copyURL(url) {
    navigator.clipboard.writeText(url);

    const buttons = document.querySelectorAll(".copy-button");

    buttons.forEach(button => {
        button.textContent = "Copied!";

        setTimeout(() => {
            button.textContent = "Copy";
        }, 1500);
    });
}


function formatDate(dateString) {
    if (!dateString) {
        return "N/A";
    }

    return new Date(dateString).toLocaleString();
}


document.addEventListener("DOMContentLoaded", () => {
    loadURLs();
});