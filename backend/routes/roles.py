from flask import Blueprint, request, jsonify
from services.postgres_service import PostgresService

roles_bp = Blueprint(
    "roles",
    __name__,
    url_prefix="/api/roles"
)

postgres = PostgresService()


@roles_bp.route("/create", methods=["POST"])
def create_role():
    try:
        data = request.get_json()
        result = postgres.create_role(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@roles_bp.route("/modify", methods=["POST"])
def modify_role():
    try:
        data = request.get_json()
        result = postgres.modify_role(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@roles_bp.route("/members", methods=["POST"])
def role_members():
    try:
        data = request.get_json()
        result = postgres.get_role_members(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
