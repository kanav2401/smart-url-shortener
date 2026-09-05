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