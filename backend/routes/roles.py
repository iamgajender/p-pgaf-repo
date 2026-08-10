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
