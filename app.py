from flask import Flask, request, render_template, send_file
import csv
import io
import time
import requests
import os

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "BrainzIDsFromCSV/1.0")
APP_CONTACT = os.getenv("APP_CONTACT", "https://github.com")

HEADERS = {
    "User-Agent": f"{APP_NAME} ({APP_CONTACT})",
    "Accept": "application/json",
}

def search_artist(name):
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {
        "query": f'artist:"{name}"',
        "fmt": "json",
        "limit": 1,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    artists = data.get("artists", [])
    if not artists:
        return None
    return artists[0]


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

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Artist", "MBID"])

        for row in reader:
            artist = row["Artist"].strip()
            mbid = ""
            try:
                result = search_artist(artist)
                if result:
                    mbid = result.get("id", "")
            except:
                pass

            writer.writerow([artist, mbid])
            time.sleep(1)  # respect rate limit

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="artisti_mbid.csv",
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
