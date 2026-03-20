# IMDO Project Progress Tracker

A starter Streamlit app for IMDO to document project progress, delays, photos, and reports.

## Features
- Executive dashboard
- Project registry
- Weekly/site progress encoder
- Planned vs actual charts
- Delay and risk page
- CSV report downloads
- Site photo uploads stored by project

## Folder structure
- app.py
- requirements.txt
- data/projects_master.csv
- data/progress_updates.csv
- data/photos/

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Add projects first in **Project Registry**
- Encode updates in **Progress Encoder**
- Uploaded photos are saved in `data/photos/<project_id>/`
