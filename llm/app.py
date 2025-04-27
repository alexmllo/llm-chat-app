from flask import Flask, request, jsonify, send_from_directory, session
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

        # Inicializa historial si no existe
    if "chat_history" not in session:
        session["chat_history"] = []

    history = session["chat_history"]
    # Usa deque para comportamiento de cola

    res = handle_query(user_query, history)

    session["chat_history"] = history
    return res

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5050)