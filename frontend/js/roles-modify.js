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
        ? `<i class="fa-solid fa-spinner fa-spin"></i> Saving...`
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

    document.getElementById("modify-role-view").hidden = false;
    document.getElementById("connection-summary").textContent =
        `${connection.username}@${connection.server_ip}:${connection.server_port}/${connection.database}`;

    loadRoleList();
    loadRoleDatabases();
});

async function loadRoleList() {
    if (!connection) return;
    const select = document.getElementById("role_name");

    try {
        const response = await fetch("/api/users/list", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(connection)
        });
        const result = await parseJsonSafely(response);
        const roles = (result && result.users) || [];

        select.innerHTML = `<option value="">Select a role</option>` +
            roles.map(r => `<option value="${escapeHtml(r)}">${escapeHtml(r)}</option>`).join("");
    } catch (error) {
        console.error(error);
        select.innerHTML = `<option value="">Could not load roles</option>`;
    }
}

async function loadRoleCurrentState() {
    if (!connection) return;
    const roleName = document.getElementById("role_name").value;
    if (!roleName) return;

    try {
        const response = await fetch("/api/users/details", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...connection, target_username: roleName })
        });
        const result = await parseJsonSafely(response);

        if (!response.ok || result.status !== "success") return;

        document.getElementById("role_type").value = result.attributes.can_login ? "login" : "nologin";
    } catch (error) {
        console.error(error);
    }
}

async function loadRoleDatabases() {
    if (!connection) return;
    const dbSelect = document.getElementById("role_database");
    dbSelect.innerHTML = `<option value="">Loading databases…</option>`;

    try {
        const response = await fetch("/api/users/databases", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(connection)
        });
        const result = await parseJsonSafely(response);
        const databases = (result && result.databases) || [];

        dbSelect.innerHTML = databases
            .map(db => `<option value="${escapeHtml(db)}">${escapeHtml(db)}</option>`)
            .join("");

        await loadRoleSchemas();
    } catch (error) {
        console.error(error);
        dbSelect.innerHTML = `<option value="">Could not load databases</option>`;
    }
}

async function loadRoleSchemas() {
    if (!connection) return;
    const targetDatabase = document.getElementById("role_database").value;
    const schemaSelect = document.getElementById("role_schema");

    if (!targetDatabase) {
        schemaSelect.innerHTML = `<option value="">Select a database first</option>`;
        return;
    }

    schemaSelect.innerHTML = `<option value="">Loading schemas…</option>`;

    try {
        const response = await fetch("/api/users/schemas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...connection, target_database: targetDatabase })
        });
        const result = await parseJsonSafely(response);
        const schemas = (result && result.schemas) || [];

        schemaSelect.innerHTML = schemas
            .map(s => `<option value="${escapeHtml(s)}" ${s === "public" ? "selected" : ""}>${escapeHtml(s)}</option>`)
            .join("");
    } catch (error) {
        console.error(error);
        schemaSelect.innerHTML = `<option value="">Could not load schemas</option>`;
    }
}

async function modifyRole() {
    if (!connection) return;

    const roleName = document.getElementById("role_name").value;
    if (!roleName) {
        const statusEl = document.getElementById("modify-role-status");
        statusEl.hidden = false;
        statusEl.className = "connection-status log-error";
        statusEl.textContent = "Select a role first.";
        return;
    }

    const databasePrivileges = ["connect", "create", "temp"]
        .filter(p => document.getElementById(`db_${p}`).checked)
        .map(p => p.toUpperCase());

    const schemaPrivileges = ["usage", "create"]
        .filter(p => document.getElementById(`schema_${p}`).checked)
        .map(p => p.toUpperCase());

    const tablePrivileges = ["select", "insert", "update", "delete", "truncate", "references", "trigger"]
        .filter(p => document.getElementById(`tbl_${p}`).checked)
        .map(p => p.toUpperCase());

    const payload = {
        ...connection,
        target_role: roleName,
        can_login: document.getElementById("role_type").value === "login",
        target_database: document.getElementById("role_database").value,
        schema: document.getElementById("role_schema").value,
        database_privileges: databasePrivileges,
        schema_privileges: schemaPrivileges,
        table_privileges: tablePrivileges,
        apply_existing: document.getElementById("apply_existing").checked,
        apply_future: document.getElementById("apply_future").checked
    };

    setButtonBusy("modify-role-btn", true, `<i class="fa-solid fa-pen"></i> Save Changes`);
    const statusEl = document.getElementById("modify-role-status");

    try {
        const response = await fetch("/api/roles/modify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await parseJsonSafely(response);

        statusEl.hidden = false;
        if (!response.ok || result.status !== "success") {
            statusEl.className = "connection-status log-error";
            statusEl.textContent = result.message || "Could not modify role.";
            return;
        }

        statusEl.className = "connection-status log-success";
        statusEl.textContent = result.message || `Role "${escapeHtml(roleName)}" updated.`;
    } catch (error) {
        console.error(error);
        statusEl.hidden = false;
        statusEl.className = "connection-status log-error";
        statusEl.textContent = error.message || "Could not reach the server.";
    } finally {
        setButtonBusy("modify-role-btn", false, `<i class="fa-solid fa-pen"></i> Save Changes`);
    }
}
