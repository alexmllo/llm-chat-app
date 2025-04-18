from flask import Flask, request, jsonify
from flask_cors import CORS

from utils.extractWebInfo import extractWebInfo

app = Flask(__name__)

CORS(app)

@app.route("/downloadWebsite", methods=["GET", "POST"])
def downloadWebsite():
    url = request.json.get('url', "")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    res = extractWebInfo(url)
    return res

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)