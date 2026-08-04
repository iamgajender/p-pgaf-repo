function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

async function parseJsonSafely(response) {
    try {
        return await response.json();
    } catch (error) {
        throw new Error(`Unexpected response from server (HTTP ${response.status}). Check the endpoint URL.`);
    }
}

function setButtonBusy(btnId, busy, idleLabel) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = busy;
    btn.innerHTML = busy
        ? `<i class="fa-solid fa-spinner fa-spin"></i> Creating...`
        : idleLabel;
}

let connection = null;

document.addEventListener("DOMContentLoaded", () => {
    const raw = sessionStorage.getItem("pgConnection");

    if (!raw) {
        document.getElementById("no-connection").hidden = false;
        return;
    }

    try {
        connection = JSON.parse(raw);
    } catch (error) {
        console.error(error);
        document.getElementById("no-connection").hidden = false;
        return;
    }

    document.getElementById("create-panel").hidden = false;
    document.getElementById("connection-summary").textContent =
        `${connection.username}@${connection.server_ip}:${connection.server_port}/${connection.database}`;
});

async function createUser() {
    if (!connection) return;

    const statusEl = document.getElementById("create-status");
    const password = document.getElementById("new_password").value;
    const confirmPassword = document.getElementById("confirm_password").value;

    if (password !== confirmPassword) {
        statusEl.hidden = false;
        statusEl.className = "connection-status log-error";
        statusEl.textContent = "Passwords do not match.";
        return;
    }

    const payload = {
        ...connection,
        new_username: document.getElementById("new_username").value.trim(),
        new_password: password,
        can_login: document.getElementById("new_can_login").checked,
        superuser: document.getElementById("new_superuser").checked,
        createdb: document.getElementById("new_createdb").checked
    };

    setButtonBusy("create-btn", true, `<i class="fa-solid fa-user-plus"></i> Create User`);

    try {
        const response = await fetch("/api/users/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await parseJsonSafely(response);

        statusEl.hidden = false;
        if (!response.ok || result.status !== "success") {
            statusEl.className = "connection-status log-error";
            statusEl.textContent = result.message || "Could not create user.";
            return;
        }

        statusEl.className = "connection-status log-success";
        statusEl.textContent = result.message || `User "${escapeHtml(payload.new_username)}" created successfully.`;
        document.getElementById("create-form").reset();
        document.getElementById("new_can_login").checked = true;
    } catch (error) {
        console.error(error);
        statusEl.hidden = false;
        statusEl.className = "connection-status log-error";
        statusEl.textContent = error.message || "Could not reach the server.";
    } finally {
        setButtonBusy("create-btn", false, `<i class="fa-solid fa-user-plus"></i> Create User`);
    }
}
