function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

function setInstallButtonState(installing) {
    const btn = document.getElementById("install-btn");
    if (!btn) return;
    btn.disabled = installing;
    btn.innerHTML = installing
        ? `<i class="fa-solid fa-spinner fa-spin"></i> Installing...`
        : `<i class="fa-solid fa-download"></i> Install PostgreSQL`;
}

async function installPostgres() {
    const postgresPassword = document.getElementById("postgres_password").value;
    const confirmPassword = document.getElementById("postgres_password_confirm").value;
    const mismatchHint = document.getElementById("password-mismatch-hint");

    if (postgresPassword !== confirmPassword) {
        mismatchHint.style.display = "block";
        return;
    }
    mismatchHint.style.display = "none";

    const deployment = {
        server_ip: document.getElementById("server_ip").value.trim(),
        ssh_user: document.getElementById("ssh_user").value.trim(),
        ssh_password: document.getElementById("ssh_password").value,
        postgres_version: document.getElementById("postgres_version").value,
        postgres_password: postgresPassword
    };

    const status = document.getElementById("status");
    status.textContent = "Starting PostgreSQL deployment...\n";
    setInstallButtonState(true);

    // Start live log polling
    const timer = setInterval(loadDeploymentLog, 2000);

    try {
        const response = await fetch("/api/install", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(deployment)
        });
        clearInterval(timer);

        if (!response.ok) {
            const error = await response.json();
            status.innerHTML = `
                <span class="log-error">❌ ${escapeHtml(error.message)}</span>
                <pre>${escapeHtml(error.stderr || "")}</pre>
            `;
            setInstallButtonState(false);
            return;
        }

        const result = await response.json();

        if (result.status !== "success") {
            status.innerHTML = `
                <span class="log-error">❌ ${escapeHtml(result.message)}</span>
                <pre>${escapeHtml(result.stderr || "")}</pre>
            `;
            setInstallButtonState(false);
            return;
        }

        if (!result.summary || !result.summary.settings) {
            status.innerHTML = `<span class="log-error">Summary file was not generated.</span>`;
            setInstallButtonState(false);
            return;
        }

        // Success — the server now has a real postgres password set (via
        // Ansible), so User Management can connect immediately without
        // anyone SSHing in to run ALTER USER manually. This mirrors the
        // exact shape users/index.html already restores on load.
        sessionStorage.setItem("pgConnection", JSON.stringify({
            server_ip: deployment.server_ip,
            server_port: "5432",
            database: "postgres",
            username: "postgres",
            password: deployment.postgres_password
        }));

        // Hand the install result to the dedicated result page and redirect.
        sessionStorage.setItem("deploymentResult", JSON.stringify(result));
        window.location.href = "result.html";
    }
    catch (error) {
        clearInterval(timer);
        console.error(error);
        status.innerHTML = `
            <span class="log-error">Backend Error</span>
            <pre>${escapeHtml(String(error))}</pre>
        `;
        setInstallButtonState(false);
    }
}

async function loadDeploymentLog() {
    try {
        const response = await fetch("/api/deployment/log");
        if (!response.ok) {
            return;
        }
        const result = await response.json();
        const status = document.getElementById("status");
        status.textContent = result.log;
        // Auto-scroll to latest log
        status.scrollTop = status.scrollHeight;
    }
    catch (error) {
        console.error(error);
    }
}
