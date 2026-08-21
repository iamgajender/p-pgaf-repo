function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

// Ansible's `-m ping` output is one block per host, each starting with a
// line like "10.1.1.242 | SUCCESS => {" or "10.1.1.153 | UNREACHABLE! => {".
// Coloring the whole output block by overall pass/fail (the old behavior)
// meant a single successful host's line still rendered in red whenever
// ANY other host failed — this splits on that per-host header line and
// colors each block independently, so SUCCESS lines are actually green
// even when the run as a whole has failures.
function formatPingOutput(rawOutput) {
    if (!rawOutput.trim()) return "";

    const hostBlockPattern = /^(\S+)\s\|\s(SUCCESS|UNREACHABLE!|FAILED!)/;
    const lines = rawOutput.split("\n");
    const blocks = [];
    let current = null;

    for (const line of lines) {
        const match = line.match(hostBlockPattern);
        if (match) {
            if (current) blocks.push(current);
            current = { status: match[2], lines: [line] };
        } else if (current) {
            current.lines.push(line);
        } else {
            // Content before the first host block (shouldn't normally
            // happen, but keep it rather than silently drop it)
            blocks.push({ status: null, lines: [line] });
        }
    }
    if (current) blocks.push(current);

    return blocks.map(block => {
        const text = block.lines.join("\n");
        const cssClass = block.status === "SUCCESS" ? "log-success"
            : (block.status === "UNREACHABLE!" || block.status === "FAILED!") ? "log-error"
            : "";
        return `<pre class="${cssClass}" style="white-space:pre-wrap; margin:6px 0; font-family:inherit;">${escapeHtml(text)}</pre>`;
    }).join("");
}

// A 404/500 from Flask often comes back as an HTML error page, not JSON
// (e.g. the route doesn't exist because Flask wasn't restarted after a
// deploy). response.json() throws a SyntaxError on that, which otherwise
// gets swallowed into a misleading "could not reach the backend" message.
async function parseJsonSafely(response) {
    try {
        return await response.json();
    } catch (error) {
        throw new Error(`Unexpected response from server (HTTP ${response.status}). The route may not exist yet — has Flask been restarted since the last deploy?`);
    }
}

function collectHAPayload() {
    return {
        monitor_ip: document.getElementById("monitor_ip").value.trim(),
        primary_ip: document.getElementById("primary_ip").value.trim(),
        standby1_ip: document.getElementById("standby1_ip").value.trim(),
        standby2_ip: document.getElementById("standby2_ip").value.trim(),
        haproxy_pgbouncer_ip: document.getElementById("haproxy_pgbouncer_ip").value.trim(),
        postgres_version: document.getElementById("postgres_version").value
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
        const result = await parseJsonSafely(response);

        statusEl.className = "connection-status";
        statusEl.innerHTML = `<div>${escapeHtml(result.message)}</div>` + formatPingOutput(result.output || "");
    } catch (error) {
        console.error(error);
        statusEl.className = "connection-status log-error";
        statusEl.textContent = error.message || "Could not reach the backend to run the connectivity check.";
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

        const result = await parseJsonSafely(response);

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
