from flask import Flask, request, jsonify
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

    res = handle_query(user_query)
    return res

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5050)