from flask import Blueprint
from flask import request
from flask import jsonify


import shutil
import subprocess
import json
import os

from utils.inventory_generator import generate_inventory
from utils.groupvars_generator import generate_group_vars
from utils.output_writer import write_deployment_output
from utils.logger import (
    backend_logger,
    ansible_logger,
    deployment_logger
)

from utils.cleanup import cleanup_previous_deployment


standalone_bp = Blueprint(
    "standalone",
    __name__,
    url_prefix="/api",
)

#
# Ansible Configuration
#
ANSIBLE_PLAYBOOK = "/usr/bin/ansible-playbook"
ANSIBLE_PROJECT = "/opt/pg_sa/pg_an"

SUMMARY_FILE = "/tmp/postgres_summary.json"


@standalone_bp.route("/install", methods=["POST"])
def install_postgresql():

    try:

        data = request.get_json()

        server_ip = data["server_ip"]
        ssh_user = data["ssh_user"]
        ssh_password = data["ssh_password"]
        postgres_version = data["postgres_version"]
        
        # clean up old logs 

        cleanup_previous_deployment()


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
        backend_logger.info(f"PWD: {os.getcwd()}")
        backend_logger.info(f"HOME: {os.environ.get('HOME')}")
        backend_logger.info(f"PATH: {os.environ.get('PATH')}")
        backend_logger.info(f"SSH: {shutil.which('ssh')}")
        backend_logger.info(f"ANSIBLE: {shutil.which('ansible-playbook')}")


        install = subprocess.run(
            [
                ANSIBLE_PLAYBOOK,
                "standalone.yml"
            ],
            cwd=ANSIBLE_PROJECT,
            capture_output=True,
            text=True
        )

        ansible_logger.info("=" * 80)
        ansible_logger.info("INSTALL STDOUT")
        ansible_logger.info(install.stdout)

        ansible_logger.info("=" * 80)
        ansible_logger.info("INSTALL STDERR")
        ansible_logger.info(install.stderr)

        ansible_logger.info("=" * 80)
        ansible_logger.info(f"RETURN CODE : {install.returncode}")

        if install.returncode != 0:

            deployment_logger.error(
                f"FAILED | Server={server_ip} | PostgreSQL={postgres_version}"
            )

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
                ANSIBLE_PLAYBOOK,
                "collect_info.yml"
            ],
            cwd=ANSIBLE_PROJECT,
            capture_output=True,
            text=True
        )

        ansible_logger.info("=" * 80)
        ansible_logger.info("COLLECT INFO STDOUT")
        ansible_logger.info(collect.stdout)

        ansible_logger.info("=" * 80)
        ansible_logger.info("COLLECT INFO STDERR")
        ansible_logger.info(collect.stderr)

        ansible_logger.info("=" * 80)
        ansible_logger.info(f"RETURN CODE : {collect.returncode}")

        if collect.returncode != 0:

            deployment_logger.error(
                f"FAILED | Server={server_ip} | PostgreSQL={postgres_version}"
            )

            return jsonify({

                "status": "failed",

                "message": "Unable to collect PostgreSQL information.",

                "stdout": collect.stdout,

                "stderr": collect.stderr

            }), 500

        #
        # Read PostgreSQL Summary
        #
        summary = {}

        if os.path.exists(SUMMARY_FILE):

            with open(SUMMARY_FILE, "r") as file:

                summary = json.load(file)

        deployment_logger.info(
            f"SUCCESS | Server={server_ip} | PostgreSQL={postgres_version}"
        )

        #
        # Success
        #
        return jsonify({

            "status": "success",

            "message": "PostgreSQL installed successfully.",

            "summary": summary

        }), 200

    except Exception as e:

        backend_logger.exception(e)

        return jsonify({

            "status": "failed",

            "message": str(e)

        }), 500
