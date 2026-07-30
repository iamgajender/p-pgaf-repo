from flask import Blueprint
from flask import request
from flask import jsonify

import subprocess
import json
import os

from utils.inventory_generator import generate_inventory
from utils.groupvars_generator import generate_group_vars
from utils.output_writer import write_deployment_output


standalone_bp = Blueprint(
    "standalone",
    __name__
)


@standalone_bp.route("/install", methods=["POST"])
def install_postgresql():

    data = request.get_json()

    server_ip = data["server_ip"]
    ssh_user = data["ssh_user"]
    ssh_password = data["ssh_password"]
    postgres_version = data["postgres_version"]

    #
    # Generate inventory.ini
    #
    generate_inventory(
        server_ip,
        ssh_user,
        ssh_password
    )

    #
    # Generate postgres.yml
    #
    generate_group_vars(
        postgres_version
    )

    #
    # Write deployment request
    #
    write_deployment_output(
        server_ip,
        ssh_user,
        postgres_version
    )

    print("=" * 70)
    print(data)
    print("=" * 70)

    #
    # Run PostgreSQL Installation Playbook
    #
    install = subprocess.run(
        [
            "ansible-playbook",
            "standalone.yml"
        ],
        cwd="/opt/pg_sa/pg_an",
        capture_output=True,
        text=True
    )

    #
    # Installation Failed
    #
    if install.returncode != 0:

        return jsonify({

            "status": "failed",

            "message": "PostgreSQL installation failed.",

            "stdout": install.stdout,

            "stderr": install.stderr

        }), 500

    #
    # Run PostgreSQL Information Collection Playbook
    #
    collect = subprocess.run(
        [
            "ansible-playbook",
            "collect_info.yml"
        ],
        cwd="/opt/pg_sa/pg_an",
        capture_output=True,
        text=True
    )

    #
    # Collection Failed
    #
    if collect.returncode != 0:

        return jsonify({

            "status": "failed",

            "message": "Unable to collect PostgreSQL information.",

            "stdout": collect.stdout,

            "stderr": collect.stderr

        }), 500

    #
    # Read Generated JSON
    #
    summary = {}

    summary_file = "/tmp/postgres_summary.json"

    if os.path.exists(summary_file):

        with open(summary_file, "r") as f:
            summary = json.load(f)

    #
    # Success Response
    #
    return jsonify({

        "status": "success",

        "message": "PostgreSQL installed successfully.",

        "summary": summary

    }), 200
