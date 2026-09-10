let clickChart = null;
let browserChart = null;
let referrerChart = null;


function getShortCode() {
    const path = window.location.pathname;
    const parts = path.split("/");

    return parts[parts.length - 1];
}


function formatDate(dateString) {
    if (!dateString) {
        return "-";
    }

    return new Date(dateString).toLocaleString();
}


function getBrowser(userAgent) {
    if (!userAgent) {
        return "Unknown";
    }

    if (userAgent.includes("Edg")) {
        return "Microsoft Edge";
    }

    if (userAgent.includes("Chrome")) {
        return "Google Chrome";
    }

    if (userAgent.includes("Firefox")) {
        return "Mozilla Firefox";
    }

    if (userAgent.includes("Safari")) {
        return "Safari";
    }

    if (userAgent.includes("Opera")) {
        return "Opera";
    }

    return "Other";
}


async function loadAnalytics() {
    const shortCode = getShortCode();

    try {
        const response = await fetch(
            `/api/urls/${shortCode}/analytics`
        );

        const data = await response.json();

        if (!response.ok) {
            showError(
                data.detail || "Unable to load analytics."
            );

            return;
        }

        displayAnalytics(data);

    } catch (error) {
        console.error(error);

        showError(
            "Unable to connect to the server."
        );
    }
}


function displayAnalytics(data) {

    document.getElementById("short-code").textContent =
        data.short_code;


    const shortUrl =
        `${window.location.origin}/${data.short_code}`;


    const shortUrlElement =
        document.getElementById("short-url");


    shortUrlElement.textContent =
        shortUrl;


    shortUrlElement.href =
        shortUrl;


    document.getElementById("original-url").textContent =
        data.original_url;


    document.getElementById("total-clicks").textContent =
        data.total_clicks;


    document.getElementById("created-at").textContent =
        formatDate(data.created_at);


    document.getElementById("expires-at").textContent =
        data.expires_at
            ? formatDate(data.expires_at)
            : "Never";


    displayClicks(data.clicks || []);

    createClickChart(data.clicks || []);

    createBrowserChart(data.browsers || []);

    createReferrerChart(data.referrers || []);
}


function displayClicks(clicks) {

    const table =
        document.getElementById("clicks-table");


    if (clicks.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="4" class="empty">
                    No clicks recorded yet.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML = clicks.map(click => `

        <tr>

            <td>
                ${formatDate(click.clicked_at)}
            </td>

            <td>
                ${click.ip_address || "Unknown"}
            </td>

            <td>
                ${getBrowser(click.user_agent)}
            </td>

            <td>
                ${click.referrer || "Direct"}
            </td>

        </tr>

    `).join("");
}


function createClickChart(clicks) {

    const canvas =
        document.getElementById("click-chart");


    if (!canvas) {
        return;
    }


    const groupedClicks = {};


    clicks.forEach(click => {

        const date =
            new Date(click.clicked_at)
                .toLocaleDateString();


        if (!groupedClicks[date]) {
            groupedClicks[date] = 0;
        }


        groupedClicks[date]++;
    });


    const labels =
        Object.keys(groupedClicks).reverse();


    const values =
        labels.map(
            date => groupedClicks[date]
        );


    if (clickChart) {
        clickChart.destroy();
    }


    clickChart = new Chart(canvas, {

        type: "line",

        data: {

            labels: labels,

            datasets: [

                {
                    label: "Clicks",

                    data: values,

                    tension: 0.3,

                    fill: true
                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            scales: {

                y: {

                    beginAtZero: true,

                    ticks: {
                        precision: 0
                    }

                }

            }

        }

    });
}


function createBrowserChart(browsers) {

    const canvas =
        document.getElementById("browser-chart");


    if (!canvas) {
        return;
    }


    const labels =
        browsers.map(item => item.browser);


    const values =
        browsers.map(item => item.clicks);


    if (browserChart) {
        browserChart.destroy();
    }


    browserChart = new Chart(canvas, {

        type: "doughnut",

        data: {

            labels: labels,

            datasets: [

                {
                    label: "Clicks",

                    data: values
                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: {
                    position: "bottom"
                }

            }

        }

    });
}


function createReferrerChart(referrers) {

    const canvas =
        document.getElementById("referrer-chart");


    if (!canvas) {
        return;
    }


    const labels =
        referrers.map(item => item.referrer);


    const values =
        referrers.map(item => item.clicks);


    if (referrerChart) {
        referrerChart.destroy();
    }


    referrerChart = new Chart(canvas, {

        type: "bar",

        data: {

            labels: labels,

            datasets: [

                {
                    label: "Clicks",

                    data: values
                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            scales: {

                y: {

                    beginAtZero: true,

                    ticks: {
                        precision: 0
                    }

                }

            }

        }

    });
}


function showError(message) {

    document.querySelector(".dashboard").innerHTML = `

        <div class="error-card">

            <h1>Unable to Load Analytics</h1>

            <p>${message}</p>

            <a href="/">
                ← Back to URL Shortener
            </a>

        </div>

    `;
}


window.addEventListener(
    "DOMContentLoaded",
    loadAnalytics
);