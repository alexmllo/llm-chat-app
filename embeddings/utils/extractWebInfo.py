import os
from urllib.parse import urlparse

from .scraper import downloadWebsite
from .createEmbeddingsDB import process_folder_files


SAVE_FOLDER = "markdowns"

def extractWebInfo(url):
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    base_folder = hostname.replace('.', '_')
    folder = os.path.join(SAVE_FOLDER, base_folder)
    os.makedirs(folder, exist_ok=True)
    downloadWebsite(url, folder)
    process_folder_files(folder)

    return "Succesfull"