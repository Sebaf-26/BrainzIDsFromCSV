import csv
import requests
import os

LIDARR_URL = os.getenv("LIDARR_URL")
LIDARR_API_KEY = os.getenv("LIDARR_API_KEY")
CSV_PATH = os.getenv("CSV_PATH", "/data/artisti_mbid.csv")

headers = {
    "X-Api-Key": LIDARR_API_KEY,
    "Content-Type": "application/json"
}

def get_root_folder():
    r = requests.get(f"{LIDARR_URL}/api/v1/rootfolder", headers=headers)
    r.raise_for_status()
    data = r.json()
    return data[0]["id"]

def get_quality_profile():
    r = requests.get(f"{LIDARR_URL}/api/v1/qualityprofile", headers=headers)
    r.raise_for_status()
    data = r.json()
    return data[0]["id"]

def artist_exists(mbid):
    r = requests.get(f"{LIDARR_URL}/api/v1/artist", headers=headers)
    r.raise_for_status()
    for artist in r.json():
        if artist.get("foreignArtistId") == mbid:
            return True
    return False

def add_artist(mbid, root_id, profile_id):
    payload = {
        "foreignArtistId": mbid,
        "monitored": False,
        "qualityProfileId": profile_id,
        "rootFolderPath": None,
        "rootFolderId": root_id,
        "addOptions": {
            "monitor": "none"
        }
    }

    r = requests.post(f"{LIDARR_URL}/api/v1/artist", json=payload, headers=headers)
    if r.status_code not in (200, 201):
        print("Error:", r.text)
    else:
        print("Added:", mbid)

def main():
    root_id = get_root_folder()
    profile_id = get_quality_profile()

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            mbid = row.get("MBID") or row.get("mbid")
            if not mbid:
                continue

            if artist_exists(mbid):
                print("Already exists:", mbid)
                continue

            add_artist(mbid, root_id, profile_id)

if __name__ == "__main__":
    main()
