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

        <a href="${data.short_url}" target="_blank">
            ${data.short_url}
        </a>

        <p>
            Clicks: ${data.clicks}
        </p>

        <a href="/api/urls/${data.short_code}/analytics"
           target="_blank">
            View Analytics
        </a>
    `;
}