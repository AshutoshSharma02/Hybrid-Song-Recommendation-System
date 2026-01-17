# Hybrid-Song-Recommendation-System

## Git LFS (Large Files)

This repository includes large data files used by the Streamlit app. To store these files efficiently and ensure successful deploys (e.g., Streamlit Cloud), use Git LFS.

Quick setup (Windows PowerShell):

```powershell
# 1) Install git-lfs (download installer from https://git-lfs.github.com or use your package manager)
git lfs install

# 2) Track the large patterns (a `.gitattributes` file is added to this repo)
git add .gitattributes

# 3) Re-commit large files so they're stored in LFS (example patterns used here)
git rm --cached data/*.npz data/*.npy data/*.joblib data/*.csv transformer.joblib || echo "No matching files to unstage"
git add data/* transformer.joblib
git commit -m "Move large data files to Git LFS"

# 4) Push to remote
git push origin main
```

Notes:
- If large files were already pushed to the remote, you may need to use the `git lfs migrate` command or follow GitHub's guidance to rewrite history.
- Streamlit Cloud supports repos with Git LFS; ensure your remote (GitHub) has LFS enabled and that your account/bandwidth limits are sufficient for the data size.
- Alternatively, host large data externally (S3, Azure Blob, or direct download URLs) and update the app to download on first run.

Auto-download support
---------------------

You can optionally host the data files on stable URLs and let the app download missing files at startup. Steps:

1. Edit `data/data_urls.json` and replace the example URLs with real download links for each file.
2. Commit `data/data_urls.json` (it contains only small text links).
3. Redeploy to Streamlit. When a required data file is missing, the app will attempt to download it from the provided URL and retry loading.

Security note: ensure public URLs are safe to expose in the repository. For private storage, add runtime code to fetch from authenticated sources instead.

Automated helper script
-----------------------

There is a PowerShell helper script to run the common Git LFS setup steps and optionally migrate history:

- `scripts/setup_git_lfs.ps1`

Run it from the repository root in PowerShell:

```powershell
.\scripts\setup_git_lfs.ps1
```

The script will check for `git` and `git lfs`, run `git lfs install`, track common file patterns, optionally unstage cached large files, commit pointer updates, and push (if you confirm). It also offers the advanced `git lfs migrate` step which rewrites history — only run that if you understand the consequences.
