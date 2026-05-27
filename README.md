# Cytoid Level Downloader

A Python scraper that **bulk-downloads all community-created levels** from [Cytoid](https://cytoid.io/) — a rhythm game that lets players publish custom music maps.

---

## What It Does

- `cytoid_downloader.py` — fetches and downloads all available music map packages from the Cytoid API
- `top_level.py` — copies the top-level files from each package for browsing

---

## Setup

```bash
# Create required folders before running
mkdir data        # downloaded level files go here
mkdir top_level   # top-level files are copied here

# Install dependencies
pip install requests

# Run the downloader
python cytoid_downloader.py
```

---

## Files

| File | Description |
|---|---|
| `cytoid_downloader.py` | Main downloader — fetches all Cytoid levels |
| `cytoid_downloader_updated_failed.py` | Retry script for failed downloads |
| `top_level.py` | Copies top-level assets from downloaded packages |

---

## Notes

- The Cytoid API is public. Downloaded content is for personal use only.
- Run the retry script after the main downloader to catch any failed requests.
- Large download — thousands of levels at varying sizes.

