from flask import Blueprint, request, jsonify

auth_bp = Blueprint(
    "auth",
    __name__
)

# Demo Users
USERS = {
    "admin": "password"
}


# -----------------------
# Login Route
# -----------------------
@auth_bp.route('/login', methods=['POST'])
def login():

    data = request.json

    username = data.get("username")

    password = data.get("password")

    if (
        username in USERS and
        USERS[username] == password
    ):

        return jsonify({
            "message": "Login successful",
            "user": username
        })

    return jsonify({
        "error": "Invalid credentials"
    }), 401