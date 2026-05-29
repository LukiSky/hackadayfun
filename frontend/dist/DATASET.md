# Dataset source

The dashboard loads CSV data from the backend, not from this folder:

- **API:** `GET /api/dataset/csv` (proxied to `http://localhost:5000` in dev)
- **Canonical file:** `backend/data/LifeChanger_Sample_Data_Populated_10000.csv`

The legacy `data.csv` copy in `public/` is no longer used. Start the backend before the frontend.
