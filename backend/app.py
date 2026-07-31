from flask import Flask
from flask_cors import CORS

from routes.standalone import standalone_bp
from routes.deployment import deployment_bp

app = Flask(__name__)

CORS(app)

app.register_blueprint(standalone_bp)
app.register_blueprint(deployment_bp)

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )
