function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

// Role Management deliberately does NOT show its own connect form — it
// reuses whatever connection User Management already established via
// sessionStorage, so the superuser doesn't have to connect twice.
document.addEventListener("DOMContentLoaded", () => {
    const raw = sessionStorage.getItem("pgConnection");

    if (!raw) {
        document.getElementById("no-connection").hidden = false;
        return;
    }

    try {
        const connection = JSON.parse(raw);
        document.getElementById("connected-view").hidden = false;
        document.getElementById("connection-summary").textContent =
            `${connection.username}@${connection.server_ip}:${connection.server_port}/${connection.database}`;
    } catch (error) {
        console.error(error);
        document.getElementById("no-connection").hidden = false;
    }
});
