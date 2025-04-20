import os
from urllib.parse import urlparse

from .scraper import downloadWebsite
from .createEmbeddingsDB import process_folder_files


SAVE_FOLDER = "markdowns"

def extractWebInfo(url, task_id, progress_dict):
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    folder = os.path.join(SAVE_FOLDER, hostname)
    os.makedirs(folder, exist_ok=True)
    downloadWebsite(url, folder, task_id, progress_dict)
    if(url.endswith("/")):
        url = url[:-1]
    process_folder_files(url, folder, task_id, progress_dict)

    return "Scraping complete"