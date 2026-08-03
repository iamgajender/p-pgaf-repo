function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

// Connection details live only in memory for the life of this page —
// never written to sessionStorage/localStorage, so the superuser
// password disappears on refresh or tab close.
let connectionInfo = null;

function setStatus(elementId, message, isError) {
    const el = document.getElementById(elementId);
    el.hidden = false;
    el.className = (elementId === "connection-status" ? "connection-status " : "modal-status ")
        + (isError ? "log-error" : "log-success");
    el.textContent = message;
}

function setButtonBusy(btnId, busy, idleLabel) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = busy;
    btn.innerHTML = busy
        ? `<i class="fa-solid fa-spinner fa-spin"></i> Working...`
        : idleLabel;
}

function openModal(modalId) {
    document.getElementById(modalId).hidden = false;
}
function closeModal(modalId) {
    document.getElementById(modalId).hidden = true;
}

async function connectDatabase() {
    const payload = {
        server_ip: document.getElementById("server_ip").value.trim(),
        server_port: document.getElementById("server_port").value.trim(),
        database: document.getElementById("db_name").value.trim(),
        username: document.getElementById("db_username").value.trim(),
        password: document.getElementById("db_password").value
    };

    setButtonBusy("connect-btn", true, `<i class="fa-solid fa-plug"></i> Connect`);

    try {
        const response = await fetch("/api/users/connect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            setStatus("connection-status", result.message || "Connection failed.", true);
            setButtonBusy("connect-btn", false, `<i class="fa-solid fa-plug"></i> Connect`);
            return;
        }

        connectionInfo = payload;
        setStatus("connection-status", result.message || `Connected to ${escapeHtml(payload.server_ip)}`, false);
        document.getElementById("user-actions").hidden = false;
        await loadUserList();
    } catch (error) {
        console.error(error);
        setStatus("connection-status", "Could not reach the server.", true);
    } finally {
        setButtonBusy("connect-btn", false, `<i class="fa-solid fa-plug"></i> Connect`);
    }
}

async function loadUserList() {
    if (!connectionInfo) return;
    try {
        const response = await fetch("/users/list", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(connectionInfo)
        });
        const result = await response.json();
        const users = (result && result.users) || [];

        [document.getElementById("modify_username"), document.getElementById("priv_username")]
            .forEach(select => {
                select.innerHTML = users
                    .map(u => `<option value="${escapeHtml(u)}">${escapeHtml(u)}</option>`)
                    .join("");
            });
    } catch (error) {
        console.error(error);
    }
}

async function createUser() {
    if (!connectionInfo) return;
    const payload = {
        ...connectionInfo,
        new_username: document.getElementById("new_username").value.trim(),
        new_password: document.getElementById("new_password").value,
        can_login: document.getElementById("new_can_login").checked,
        superuser: document.getElementById("new_superuser").checked,
        createdb: document.getElementById("new_createdb").checked
    };

    setButtonBusy("create-submit-btn", true, "Create");
    try {
        const response = await fetch("/users/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            setStatus("create-status", result.message || "Could not create user.", true);
            return;
        }

        setStatus("create-status", result.message || "User created.", false);
        await loadUserList();
        setTimeout(() => closeModal("modal-create"), 1200);
    } catch (error) {
        console.error(error);
        setStatus("create-status", "Could not reach the server.", true);
    } finally {
        setButtonBusy("create-submit-btn", false, "Create");
    }
}

async function modifyUser() {
    if (!connectionInfo) return;
    const payload = {
        ...connectionInfo,
        username: document.getElementById("modify_username").value,
        password: document.getElementById("modify_password").value || null,
        can_login: document.getElementById("modify_can_login").checked,
        superuser: document.getElementById("modify_superuser").checked
    };

    setButtonBusy("modify-submit-btn", true, "Save Changes");
    try {
        const response = await fetch("/users/modify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            setStatus("modify-status", result.message || "Could not modify user.", true);
            return;
        }

        setStatus("modify-status", result.message || "User updated.", false);
        setTimeout(() => closeModal("modal-modify"), 1200);
    } catch (error) {
        console.error(error);
        setStatus("modify-status", "Could not reach the server.", true);
    } finally {
        setButtonBusy("modify-submit-btn", false, "Save Changes");
    }
}

async function updatePrivileges() {
    if (!connectionInfo) return;
    const privileges = ["select", "insert", "update", "delete", "all"]
        .filter(p => document.getElementById(`priv_${p}`).checked)
        .map(p => p.toUpperCase());

    const payload = {
        ...connectionInfo,
        username: document.getElementById("priv_username").value,
        target_database: document.getElementById("priv_database").value.trim(),
        action: document.getElementById("priv_action").value,
        privileges
    };

    setButtonBusy("privileges-submit-btn", true, "Apply");
    try {
        const response = await fetch("/users/privileges", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            setStatus("privileges-status", result.message || "Could not update privileges.", true);
            return;
        }

        setStatus("privileges-status", result.message || "Privileges updated.", false);
        setTimeout(() => closeModal("modal-privileges"), 1200);
    } catch (error) {
        console.error(error);
        setStatus("privileges-status", "Could not reach the server.", true);
    } finally {
        setButtonBusy("privileges-submit-btn", false, "Apply");
    }
}
