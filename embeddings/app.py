import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import uuid
import signal
import sys
import shutil

from utils.extractWebInfo import extractWebInfo

app = Flask(__name__)

CORS(app)

progress_dict = {}

MARKDOWNS_DIR = "markdowns"


def cleanup_on_exit(signum, frame):
    print("Received shutdown signal. Cleaning up markdowns folder...")

    if os.path.exists(MARKDOWNS_DIR):
        shutil.rmtree(MARKDOWNS_DIR)
        print(f"Deleted contents of {MARKDOWNS_DIR} folder.")
    else:
        print(f"{MARKDOWNS_DIR} folder does not exist. No cleanup needed.")
    
    sys.exit(0)


# Register cleanup signal handlers
signal.signal(signal.SIGINT, cleanup_on_exit)   # Handles Ctrl+C
signal.signal(signal.SIGTERM, cleanup_on_exit)  # Handles docker stop


@app.route("/downloadWebsite", methods=["GET", "POST"])
def downloadWebsite():
    url = request.json.get('url', "")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    task_id = str(uuid.uuid4())
    progress_dict[task_id] =  {
        "status": "working",
        "text": "Starting..."
    }

    thread = threading.Thread(target=process_website_task, args=(task_id, url))
    thread.start()

    return jsonify({"task_id": task_id})


def process_website_task(task_id, url):
    try:
        progress_dict[task_id] =  {
        "status": "working",
        "text": "Starting..."
        }
        extractWebInfo(url, task_id, progress_dict)
        progress_dict[task_id]['status'] = "done"
        progress_dict[task_id]['text'] += f"\n✅ Finished scrapping {url}!"
    except Exception as e:
        progress_dict[task_id] = {"status":"error", "text":str(e)}


@app.route("/progress/<task_id>")
def get_progress(task_id):
    data = progress_dict.get(task_id)
    if data is None:
        return jsonify({"status": "not_found", "text": ""})

    #If status is error or finished, remove from progresses
    if data["status"] != "working":
        progress_dict.pop(task_id)
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)