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

    document.getElementById("members-view").hidden = false;
    document.getElementById("connection-summary").textContent =
        `${connection.username}@${connection.server_ip}:${connection.server_port}/${connection.database}`;

    loadRoleOptions();
});

async function loadRoleOptions() {
    if (!connection) return;
    const select = document.getElementById("member_role");

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

async function loadMembers() {
    if (!connection) return;
    const roleName = document.getElementById("member_role").value;
    const listEl = document.getElementById("members-list");

    if (!roleName) {
        listEl.innerHTML = `<span class="field-hint">Select a role above to see its members.</span>`;
        return;
    }

    listEl.innerHTML = `<span class="field-hint">Loading members…</span>`;

    try {
        const response = await fetch("/api/roles/members", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...connection, target_role: roleName })
        });
        const result = await parseJsonSafely(response);

        if (!response.ok || result.status !== "success") {
            listEl.innerHTML = `<span class="field-hint" style="color:var(--signal-red);">${escapeHtml(result.message || "Could not load members.")}</span>`;
            return;
        }

        const members = result.members || [];
        listEl.innerHTML = members.length
            ? `<table class="summary-table">
                 <tr><th>Member</th></tr>
                 ${members.map(m => `<tr><td>${escapeHtml(m)}</td></tr>`).join("")}
               </table>`
            : `<span class="field-hint">No members assigned to "${escapeHtml(roleName)}" yet.</span>`;
    } catch (error) {
        console.error(error);
        listEl.innerHTML = `<span class="field-hint" style="color:var(--signal-red);">Could not reach the server.</span>`;
    }
}
