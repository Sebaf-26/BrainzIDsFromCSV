from flask import Flask, request, render_template
import csv
import io
import time
import requests
import os

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "BrainzIDsFromCSV/1.0")
APP_CONTACT = os.getenv("APP_CONTACT", "https://github.com")
LIDARR_URL = os.getenv("LIDARR_URL")
LIDARR_API_KEY = os.getenv("LIDARR_API_KEY")

HEADERS_MB = {
    "User-Agent": f"{APP_NAME} ({APP_CONTACT})",
    "Accept": "application/json",
}

HEADERS_LIDARR = {
    "X-Api-Key": LIDARR_API_KEY,
    "Content-Type": "application/json"
}


def search_artist(name):
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {
        "query": f'artist:"{name}"',
        "fmt": "json",
        "limit": 1,
    }
    r = requests.get(url, params=params, headers=HEADERS_MB, timeout=20)
    r.raise_for_status()
    data = r.json()
    artists = data.get("artists", [])
    if not artists:
        return None
    return artists[0]


def get_root_folder():
    r = requests.get(f"{LIDARR_URL}/api/v1/rootfolder", headers=HEADERS_LIDARR)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise Exception("Nessuna root folder configurata in Lidarr")
    return data[0]["path"]


def get_quality_profile():
    r = requests.get(f"{LIDARR_URL}/api/v1/qualityprofile", headers=HEADERS_LIDARR)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise Exception("Nessun quality profile configurato in Lidarr")
    return data[0]["id"]


def get_metadata_profile():
    r = requests.get(f"{LIDARR_URL}/api/v1/metadataprofile", headers=HEADERS_LIDARR)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise Exception("Nessun metadata profile configurato")
    return data[0]["id"]


def artist_exists(mbid):
    r = requests.get(f"{LIDARR_URL}/api/v1/artist", headers=HEADERS_LIDARR)
    r.raise_for_status()
    for artist in r.json():
        if artist.get("foreignArtistId") == mbid:
            return True
    return False


def add_artist(name, mbid, root_path, quality_id, metadata_id):
    payload = {
        "artistName": name,
        "foreignArtistId": mbid,
        "monitored": False,
        "qualityProfileId": quality_id,
        "metadataProfileId": metadata_id,
        "rootFolderPath": root_path,
        "addOptions": {
            "monitor": "none"
        }
    }

    r = requests.post(
        f"{LIDARR_URL}/api/v1/artist",
        json=payload,
        headers=HEADERS_LIDARR
    )

    if r.status_code in (200, 201):
        return True
    else:
        raise Exception(r.text)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return "No file uploaded", 400

        content = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        if "Artist" not in reader.fieldnames:
            return "CSV must contain 'Artist' column", 400

        results = []

        try:
            root_path = get_root_folder()
            quality_id = get_quality_profile()
            metadata_id = get_metadata_profile()
        except Exception as e:
            return f"Errore configurazione Lidarr: {str(e)}", 500

        for row in reader:
            artist = row["Artist"].strip()
            mbid = ""
            status = "non trovato"

            try:
                result = search_artist(artist)
                if result:
                    mbid = result.get("id", "")

                    if artist_exists(mbid):
                        status = "già presente"
                    else:
                        add_artist(artist, mbid, root_path, quality_id, metadata_id)
                        status = "aggiunto"
            except Exception as e:
                status = f"errore: {str(e)}"

            results.append({
                "artist": artist,
                "mbid": mbid,
                "status": status
            })

            time.sleep(1)

        return render_template("index.html", results=results)

    return render_template("index.html", results=None)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
