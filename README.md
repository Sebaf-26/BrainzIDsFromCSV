# BrainzIDsFromCSV

Web tool per convertire una lista di artisti in **MusicBrainz IDs (MBID)** e importarli automaticamente in **Lidarr** senza attivare il monitoraggio.

Progettato per essere deployato facilmente tramite **Docker** e **Portainer** direttamente da repository GitHub.

---

## Funzionalità

- Interfaccia web semplice
- Upload CSV con lista artisti
- Ricerca automatica MBID tramite MusicBrainz
- Import automatico su Lidarr
- Artisti aggiunti **non monitored**
- Nessuna ricerca automatica di album
- Deploy rapido con Docker Compose

---

## Requisiti

- Docker
- Portainer (opzionale ma consigliato)
- Lidarr funzionante
- API key di Lidarr

---

## Struttura del progetto

