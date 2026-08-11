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

    loadAvailableRoles();
});

function toggleAccessModel() {
    const isRbac = document.getElementById("mode_rbac").checked;
    document.getElementById("rbac-section").hidden = !isRbac;
    document.getElementById("custom-section").hidden = isRbac;
    document.getElementById("assign_role").required = isRbac;
}

async function loadAvailableRoles() {
    if (!connection) return;
    const roleSelect = document.getElementById("assign_role");

    try {
        const response = await fetch("/api/users/list", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(connection)
        });
        const result = await parseJsonSafely(response);
        const users = (result && result.users) || [];

        // Filter to NOLOGIN roles only — these are the group roles that
        // are meant to be assigned to users, not login accounts themselves.
        // We detect this by fetching role details, but that's N+1 calls.
        // Simpler: filter out known system roles and anything that looks
        // like a login account (contains a dot or @ which is typical of
        // user accounts). The backend's list already excludes pg_* roles.
        // We show everything and let the admin pick — the UI label makes
        // it clear this is for role assignment.
        roleSelect.innerHTML = `<option value="">Select a role to assign</option>` +
            users.map(u => `<option value="${escapeHtml(u)}">${escapeHtml(u)}</option>`).join("");
    } catch (error) {
        console.error(error);
        roleSelect.innerHTML = `<option value="">Could not load roles</option>`;
    }
}

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

    const isRbac = document.getElementById("mode_rbac").checked;

    const payload = {
        ...connection,
        new_username: document.getElementById("new_username").value.trim(),
        new_password: password,
        access_model: isRbac ? "rbac" : "custom",
        // RBAC fields
        assign_role: isRbac ? document.getElementById("assign_role").value : null,
        set_default_role: isRbac ? document.getElementById("set_default_role").checked : false,
        // Custom fields
        can_login: !isRbac ? document.getElementById("new_can_login").checked : true,
        superuser: !isRbac ? document.getElementById("new_superuser").checked : false,
        createdb: !isRbac ? document.getElementById("new_createdb").checked : false
    };

    if (isRbac && !payload.assign_role) {
        statusEl.hidden = false;
        statusEl.className = "connection-status log-error";
        statusEl.textContent = "Please select a role to assign.";
        return;
    }

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
        toggleAccessModel();
        await loadAvailableRoles();
    } catch (error) {
        console.error(error);
        statusEl.hidden = false;
        statusEl.className = "connection-status log-error";
        statusEl.textContent = error.message || "Could not reach the server.";
    } finally {
        setButtonBusy("create-btn", false, `<i class="fa-solid fa-user-plus"></i> Create User`);
    }
}
