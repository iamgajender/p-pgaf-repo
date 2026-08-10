document.addEventListener("DOMContentLoaded", () => {
    const raw = sessionStorage.getItem("deploymentResult");
    const panel = document.getElementById("result-panel");

    if (!raw) {
        panel.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-circle-info"></i>
                <p>No deployment result found. Start a new installation to see results here.</p>
                <div class="result-actions" style="justify-content:center;">
                    <a class="btn btn-primary" href="install.html">Start Installation</a>
                </div>
            </div>
        `;
        return;
    }

    try {
        const result = JSON.parse(raw);
        renderResult(result);
    } catch (error) {
        console.error(error);
        panel.innerHTML = `
            <div class="result-status error">
                <i class="fa-solid fa-circle-xmark"></i>
                Could not read the deployment result.
            </div>
        `;
    } finally {
        // One-time view — don't let a page refresh re-show a stale result.
        sessionStorage.removeItem("deploymentResult");
    }
});

function renderResult(result) {
    const panel = document.getElementById("result-panel");
    const isSuccess = result.status === "success";

    let html = `
        <div class="result-status ${isSuccess ? "success" : "error"}">
            <i class="fa-solid ${isSuccess ? "fa-circle-check" : "fa-circle-xmark"}"></i>
            ${escapeHtml(result.message || (isSuccess ? "Deployment completed" : "Deployment failed"))}
        </div>
    `;

    if (!isSuccess) {
        html += `<pre>${escapeHtml(result.stderr || "")}</pre>`;
    } else if (result.summary) {
        html += `
            <hr>
            <h3>Server Information</h3>
            <table class="summary-table">
                <tr><td>Hostname</td><td>${escapeHtml(result.summary.hostname)}</td></tr>
                <tr><td>PostgreSQL Version</td><td>${escapeHtml(result.summary.postgres_version)}</td></tr>
            </table>
            <hr>
            <h3>PostgreSQL Configuration</h3>
            <table class="summary-table">
                <tr><th>Parameter</th><th>Value</th></tr>
                ${(result.summary.settings || []).map(setting => {
                    const parts = setting.split("=");
                    return `<tr><td>${escapeHtml(parts[0])}</td><td>${escapeHtml(parts[1] || "")}</td></tr>`;
                }).join("")}
            </table>
        `;
    }

    html += `
        <div class="result-actions">
            <a class="btn btn-primary" href="../index.html">Back to Dashboard</a>
            ${isSuccess ? `<a class="btn btn-primary" href="../users/index.html">Manage Users</a>` : ""}
            <a class="btn btn-outline" href="install.html">Install Another Server</a>
        </div>
    `;

    panel.innerHTML = html;
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}
