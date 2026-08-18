function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

function collectHAPayload() {
    return {
        monitor_ip: document.getElementById("monitor_ip").value.trim(),
        primary_ip: document.getElementById("primary_ip").value.trim(),
        standby1_ip: document.getElementById("standby1_ip").value.trim(),
        standby2_ip: document.getElementById("standby2_ip").value.trim(),
        haproxy_pgbouncer_ip: document.getElementById("haproxy_pgbouncer_ip").value.trim(),
        postgres_version: document.getElementById("postgres_version").value,
        ssh_user: document.getElementById("ssh_user").value.trim(),
        ssh_password: document.getElementById("ssh_password").value
    };
}

function setButtonBusy(btnId, busy, idleHtml, busyLabel) {
    const btn = document.getElementById(btnId);
    btn.disabled = busy;
    btn.innerHTML = busy
        ? `<i class="fa-solid fa-spinner fa-spin"></i> ${busyLabel}`
        : idleHtml;
}

async function testConnectivity() {
    const payload = collectHAPayload();
    const statusEl = document.getElementById("connectivity-status");

    setButtonBusy(
        "test-connectivity-btn", true,
        `<i class="fa-solid fa-plug-circle-check"></i> Test Connectivity`,
        "Testing..."
    );
    statusEl.hidden = false;
    statusEl.className = "connection-status";
    statusEl.textContent = "Checking SSH connectivity to all 4 nodes...";

    try {
        const response = await fetch("/api/ha/test-connection", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        statusEl.className = "connection-status " + (result.status === "success" ? "log-success" : "log-error");
        statusEl.textContent = `${result.message}\n\n${result.output || ""}`.trim();
    } catch (error) {
        console.error(error);
        statusEl.className = "connection-status log-error";
        statusEl.textContent = "Could not reach the backend to run the connectivity check.";
    } finally {
        setButtonBusy(
            "test-connectivity-btn", false,
            `<i class="fa-solid fa-plug-circle-check"></i> Test Connectivity`,
            ""
        );
    }
}

async function deployHA() {
    const payload = collectHAPayload();

    const status = document.getElementById("status");
    status.textContent = "Starting pg_auto_failover deployment...\nThis deploys monitor, primary, both secondaries, and HAProxy/PgBouncer — expect this to take several minutes.\n";
    setButtonBusy(
        "deploy-ha-btn", true,
        `<i class="fa-solid fa-network-wired"></i> Deploy pg_auto_failover Cluster`,
        "Deploying..."
    );

    const timer = setInterval(loadHALog, 2000);

    try {
        const response = await fetch("/api/ha/deploy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        clearInterval(timer);

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            status.innerHTML = `
                <span class="log-error">❌ ${escapeHtml(result.message || "Deployment failed.")}</span>
                <pre>${escapeHtml(result.stderr || "")}</pre>
            `;
            setButtonBusy(
                "deploy-ha-btn", false,
                `<i class="fa-solid fa-network-wired"></i> Deploy pg_auto_failover Cluster`, ""
            );
            return;
        }

        status.innerHTML = `<span class="log-success">✅ ${escapeHtml(result.message)}</span>`;
        setButtonBusy(
            "deploy-ha-btn", false,
            `<i class="fa-solid fa-network-wired"></i> Deploy pg_auto_failover Cluster`, ""
        );
    } catch (error) {
        clearInterval(timer);
        console.error(error);
        status.innerHTML = `
            <span class="log-error">Backend Error</span>
            <pre>${escapeHtml(String(error))}</pre>
        `;
        setButtonBusy(
            "deploy-ha-btn", false,
            `<i class="fa-solid fa-network-wired"></i> Deploy pg_auto_failover Cluster`, ""
        );
    }
}

async function loadHALog() {
    try {
        const response = await fetch("/api/ha/log");
        if (!response.ok) return;
        const result = await response.json();
        const status = document.getElementById("status");
        status.textContent = result.log;
        status.scrollTop = status.scrollHeight;
    } catch (error) {
        console.error(error);
    }
}
