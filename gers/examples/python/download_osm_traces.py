import requests
import os
import constants

if __name__ == "__main__":
    x_min = -83.7224203
    y_min = 32.7740929
    x_max = -83.5856634
    y_max = 32.8910234

    start_page = 0
    end_page = 100

    if not os.path.exists(constants.RAW_TRACES_DOWNLOAD_DIR):
        os.makedirs(constants.RAW_TRACES_DOWNLOAD_DIR)

    while True:
        file_name = os.path.join(constants.RAW_TRACES_DOWNLOAD_DIR, rf"osm-traces-page-{start_page}.gpx")
        url = f"https://api.openstreetmap.org/api/0.6/trackpoints?bbox={x_min},{y_min},{x_max},{y_max}&page={start_page}"
        print(rf"Downloading from {url} to {file_name} ...")
        response = requests.get(url)
        with open(file_name, "w") as f:
            f.write(response.text)
        if start_page >= end_page:
            break
        start_page += 1
