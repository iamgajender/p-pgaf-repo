from flask import Blueprint
from flask import request
from flask import jsonify

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

    return jsonify({

        "status": "success",

        "message": "Ansible inventory and group_vars generated successfully."

    }), 200
