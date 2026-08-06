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

// A 404/500 from Flask often comes back as an HTML error page, not JSON.
// response.json() throws a SyntaxError on that, which otherwise gets
// swallowed into a misleading "could not reach the server" message.
// This makes that failure mode say what it actually is.
async function parseJsonSafely(response) {
    try {
        return await response.json();
    } catch (error) {
        throw new Error(`Unexpected response from server (HTTP ${response.status}). Check the endpoint URL.`);
    }
}

function openModal(modalId) {
    document.getElementById(modalId).hidden = false;
    if (modalId === "modal-modify") {
        loadUserDetails();
    }
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
        const result = await parseJsonSafely(response);

        if (!response.ok || result.status !== "success") {
            setStatus("connection-status", result.message || "Connection failed.", true);
            setButtonBusy("connect-btn", false, `<i class="fa-solid fa-plug"></i> Connect`);
            return;
        }

        connectionInfo = payload;
        // Create User (and eventually Modify/Privileges) navigate to their
        // own page, so the connection has to survive that navigation.
        // sessionStorage clears itself when the tab closes, but note this
        // does mean the superuser password briefly sits in browser storage
        // rather than only in memory.
        sessionStorage.setItem("pgConnection", JSON.stringify(payload));
        setStatus("connection-status", result.message || `Connected to ${escapeHtml(payload.server_ip)}`, false);
        document.getElementById("user-actions").hidden = false;
        await loadUserList();
    } catch (error) {
        console.error(error);
        setStatus("connection-status", error.message || "Could not reach the server.", true);
    } finally {
        setButtonBusy("connect-btn", false, `<i class="fa-solid fa-plug"></i> Connect`);
    }
}

async function loadUserList() {
    if (!connectionInfo) return;
    try {
        const response = await fetch("/api/users/list", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(connectionInfo)
        });
        const result = await parseJsonSafely(response);
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

async function loadUserDetails() {
    if (!connectionInfo) return;
    const username = document.getElementById("modify_username").value;
    if (!username) return;

    try {
        const response = await fetch("/api/users/details", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...connectionInfo, target_username: username })
        });
        const result = await parseJsonSafely(response);

        if (!response.ok || result.status !== "success") {
            console.error(result.message);
            return;
        }

        document.getElementById("modify_can_login").checked = !!result.attributes.can_login;
        document.getElementById("modify_superuser").checked = !!result.attributes.superuser;
        document.getElementById("modify_password").value = "";
    } catch (error) {
        console.error(error);
    }
}

async function modifyUser() {
    if (!connectionInfo) return;
    // NOTE: these keys deliberately do NOT reuse "username"/"password" —
    // connectionInfo already has fields with those exact names holding
    // the SUPERUSER's login. Spreading connectionInfo and then setting
    // username/password again here would silently overwrite the
    // superuser's credentials with the target user's name and new
    // password, and the backend would try to connect AS the target user
    // (this was the "password authentication failed for user X" bug).
    const payload = {
        ...connectionInfo,
        target_username: document.getElementById("modify_username").value,
        new_password: document.getElementById("modify_password").value || null,
        can_login: document.getElementById("modify_can_login").checked,
        superuser: document.getElementById("modify_superuser").checked
    };

    setButtonBusy("modify-submit-btn", true, "Save Changes");
    try {
        const response = await fetch("/api/users/modify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await parseJsonSafely(response);

        if (!response.ok || result.status !== "success") {
            setStatus("modify-status", result.message || "Could not modify user.", true);
            return;
        }

        setStatus("modify-status", result.message || "User updated.", false);
        setTimeout(() => closeModal("modal-modify"), 1200);
    } catch (error) {
        console.error(error);
        setStatus("modify-status", error.message || "Could not reach the server.", true);
    } finally {
        setButtonBusy("modify-submit-btn", false, "Save Changes");
    }
}

async function updatePrivileges() {
    if (!connectionInfo) return;
    const privileges = ["select", "insert", "update", "delete", "all"]
        .filter(p => document.getElementById(`priv_${p}`).checked)
        .map(p => p.toUpperCase());

    // Same collision fix as modifyUser() — target_username instead of
    // username, so connectionInfo's superuser username survives the spread.
    const payload = {
        ...connectionInfo,
        target_username: document.getElementById("priv_username").value,
        target_database: document.getElementById("priv_database").value.trim(),
        action: document.getElementById("priv_action").value,
        privileges
    };

    setButtonBusy("privileges-submit-btn", true, "Apply");
    try {
        const response = await fetch("/api/users/privileges", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await parseJsonSafely(response);

        if (!response.ok || result.status !== "success") {
            setStatus("privileges-status", result.message || "Could not update privileges.", true);
            return;
        }

        setStatus("privileges-status", result.message || "Privileges updated.", false);
        setTimeout(() => closeModal("modal-privileges"), 1200);
    } catch (error) {
        console.error(error);
        setStatus("privileges-status", error.message || "Could not reach the server.", true);
    } finally {
        setButtonBusy("privileges-submit-btn", false, "Apply");
    }
}
