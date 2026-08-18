from flask import Blueprint
from flask import request
from flask import jsonify

import os
import subprocess

ha_bp = Blueprint(
    "ha",
    __name__,
    url_prefix="/api/ha",
)

#
# pg_auto_failover project (separate from /opt/pg_sa/pg_an — this is the
# HA cluster deployment described in /opt/pgaf/site.yml)
#
ANSIBLE_BIN = "/usr/bin/ansible"
ANSIBLE_PLAYBOOK = "/usr/bin/ansible-playbook"
HA_PROJECT = "/opt/pgaf"
HA_INVENTORY_FILE = f"{HA_PROJECT}/inventory/inventory.ini"

# Separate log file from the standalone install's ansible.log — these are
# two independent deployment flows and could in principle overlap.
HA_ANSIBLE_LOG = "/opt/pg_sa/backend/logs/ha_ansible.log"

HA_REQUIRED_FIELDS = [
    "monitor_ip", "primary_ip", "standby1_ip", "standby2_ip",
    "haproxy_pgbouncer_ip", "ssh_password"
]


def generate_ha_inventory(data):
    """
    Builds inventory.ini with monitor/primary/standby (2 fixed secondaries),
    haproxy+pgbouncer (same node), and [all:vars] for SSH connection
    details.
    """
    monitor_ip = data["monitor_ip"]
    primary_ip = data["primary_ip"]
    standby1_ip = data["standby1_ip"]
    standby2_ip = data["standby2_ip"]
    haproxy_pgbouncer_ip = data["haproxy_pgbouncer_ip"]
    ssh_user = data.get("ssh_user") or "root"
    ssh_password = data["ssh_password"]

    inventory = f"""[monitor]
{monitor_ip}

[primary]
{primary_ip}

[standby]
{standby1_ip}
{standby2_ip}

[haproxy]
{haproxy_pgbouncer_ip}

[pgbouncer]
{haproxy_pgbouncer_ip}

[database:children]
primary
standby

[all:vars]
ansible_user={ssh_user}
ansible_ssh_pass={ssh_password}
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
"""

    os.makedirs(os.path.dirname(HA_INVENTORY_FILE), exist_ok=True)
    with open(HA_INVENTORY_FILE, "w") as f:
        f.write(inventory)


def run_ha_playbook_live(postgres_version):
    """
    Same live-streaming pattern as standalone.py's run_playbook_live().
    postgres_version is passed as an Ansible extra-var (-e) rather than
    editing group_vars/all.yml directly.
    """
    with open(HA_ANSIBLE_LOG, "a") as log_file:

        log_file.write(f"\n{'=' * 80}\n>>> Deploying pg_auto_failover cluster (PostgreSQL {postgres_version})\n{'=' * 80}\n")
        log_file.flush()

        process = subprocess.Popen(
            [
                ANSIBLE_PLAYBOOK,
                "-i", HA_INVENTORY_FILE,
                "-e", f"postgres_version={postgres_version}",
                "site.yml"
            ],
            cwd=HA_PROJECT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
                "ANSIBLE_FORCE_COLOR": "False",
                "ANSIBLE_STDOUT_CALLBACK": "minimal",
            },
        )

        returncode = process.wait()

    return returncode


@ha_bp.route("/test-connection", methods=["POST"])
def test_connection():
    """
    Pre-flight check — runs Ansible's ping module (a real SSH connect +
    auth + Python-interpreter check, not an ICMP ping) against every host
    in the inventory that would be used for a real deploy. Lets the
    admin catch a bad password / unreachable host / missing Python
    BEFORE committing to a multi-minute site.yml run.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Request body is empty."}), 400

        missing = [f for f in HA_REQUIRED_FIELDS if not data.get(f)]
        if missing:
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing)}"
            }), 400

        generate_ha_inventory(data)

        result = subprocess.run(
            [ANSIBLE_BIN, "-i", HA_INVENTORY_FILE, "all", "-m", "ping"],
            cwd=HA_PROJECT,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "ANSIBLE_FORCE_COLOR": "False"}
        )

        output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        all_reachable = result.returncode == 0

        return jsonify({
            "status": "success" if all_reachable else "error",
            "message": (
                "All nodes reachable — SSH auth and Python interpreter OK."
                if all_reachable else
                "One or more nodes failed the connectivity check — see output below."
            ),
            "output": output
        }), 200

    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "message": "Connectivity check timed out after 30s — a host may be unreachable or firewalled."
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@ha_bp.route("/deploy", methods=["POST"])
def deploy_ha():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "failed",
                "message": "Request body is empty."
            }), 400

        required_fields = HA_REQUIRED_FIELDS + ["postgres_version"]
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return jsonify({
                "status": "failed",
                "message": f"Missing required fields: {', '.join(missing)}"
            }), 400

        # Clean log for this run, same reasoning as the standalone flow.
        open(HA_ANSIBLE_LOG, "w").close()

        generate_ha_inventory(data)

        returncode = run_ha_playbook_live(data["postgres_version"])

        if returncode != 0:
            with open(HA_ANSIBLE_LOG, "r") as log_file:
                full_log = log_file.read()

            return jsonify({
                "status": "failed",
                "message": "pg_auto_failover deployment failed.",
                "stderr": full_log
            }), 500

        return jsonify({
            "status": "success",
            "message": f'pg_auto_failover cluster (PostgreSQL {data["postgres_version"]}) deployed successfully.'
        }), 200

    except Exception as e:
        return jsonify({
            "status": "failed",
            "message": str(e)
        }), 500


@ha_bp.route("/log", methods=["GET"])
def ha_log():
    if not os.path.exists(HA_ANSIBLE_LOG):
        return jsonify({"log": ""})

    with open(HA_ANSIBLE_LOG, "r") as f:
        log = f.read()

    return jsonify({"log": log})
