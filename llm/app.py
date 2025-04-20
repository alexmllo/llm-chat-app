from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from utils.llm import handle_query

app = Flask(__name__)

CORS(app)

@app.route("/query", methods=["GET", "POST"])
def query():
    if request.method == "POST":
        user_query = request.json.get("query", "")
    else:  # GET
        user_query = request.args.get("query", "")

    if not user_query:
        return jsonify({"error": "No query provided"}), 400

    res, success = handle_query(user_query)
    if not success:
        return Response(res, status=500, mimetype="text/plain")
    return Response(res, mimetype="text/plain")

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5050)