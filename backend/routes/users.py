from flask import Blueprint, request, jsonify
from services.postgres_service import PostgresService
users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users"
)
postgres = PostgresService()
@users_bp.route("/connect", methods=["POST"])
def connect():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is empty."
            }), 400
        required_fields = [
            "server_ip",
            "server_port",
            "database",
            "username",
            "password"
        ]
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif str(data[field]).strip() == "":
                missing_fields.append(field)
        if missing_fields:
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        result = postgres.test_connection(
         data
        )
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
###############################################################
@users_bp.route("/list", methods=["POST"])
def list_users():
    try:
        data = request.get_json()
        # PostgresService.list_users() takes the whole data dict
        # (matching every other service method), not individual
        # host=/port=/etc keyword arguments — the previous call here
        # raised a TypeError on every request, which meant the Modify
        # User / Privileges dropdowns silently got an empty user list.
        result = postgres.list_users(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
###############################################################
@users_bp.route("/create", methods=["POST"])
def create_user():
    try:
        data = request.get_json()
        result = postgres.create_user(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
###############################################################
@users_bp.route("/details", methods=["POST"])
def user_details():
    try:
        data = request.get_json()
        result = postgres.get_user_details(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
###############################################################
@users_bp.route("/modify", methods=["POST"])
def modify_user():
    try:
        data = request.get_json()
        result = postgres.modify_user(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
###############################################################
@users_bp.route("/privileges", methods=["POST"])
def update_privileges():
    try:
        data = request.get_json()
        result = postgres.update_privileges(data)
        if result["status"] == "success":
            return jsonify(result), 200
        return jsonify(result), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
