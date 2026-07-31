from flask import Blueprint
from flask import jsonify
import os

deployment_bp = Blueprint(
    "deployment",
    __name__
)

ANSIBLE_LOG = "/opt/pg_sa/backend/logs/ansible.log"


@deployment_bp.route("/deployment/log", methods=["GET"])
def deployment_log():

    if not os.path.exists(ANSIBLE_LOG):

        return jsonify({

            "log": ""

        })

    with open(ANSIBLE_LOG, "r") as file:

        log = file.read()

    return jsonify({

        "log": log

    })
