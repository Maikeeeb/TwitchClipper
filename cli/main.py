import datetime
import os
import shutil
import time
from datetime import date

from backend.oneVideo import compile as comp
from backend.pipeline import scrape_filter_rank_download

base_dir = os.path.dirname(__file__)
repo_root = os.path.abspath(os.path.join(base_dir, os.pardir))
current_videos_dir = os.path.join(repo_root, "currentVideos")
os.makedirs(current_videos_dir, exist_ok=True)

while True:
    start_time = time.time()
    currentdate = datetime.datetime.today().weekday()

    main_file_path = os.path.join(base_dir, "mainFile")
    with open(main_file_path, "r") as link_file:
        streamer_names = [line.strip() for line in link_file if line.strip()]

    for filename in os.listdir(current_videos_dir):
        file_path = os.path.join(current_videos_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            print("Deleted %s" % file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    scrape_filter_rank_download(streamer_names, current_videos_dir)

    while True:
        try:
            comp("compilation_" + str(date.today()))
            break
        except OSError:
            pass
    print("--- %s seconds ---" % (time.time() - start_time))
    time.sleep(10)
    while True:
        if currentdate != datetime.datetime.today().weekday():
            break
        time.sleep(10)
