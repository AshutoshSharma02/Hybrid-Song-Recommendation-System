import streamlit as st
from content_based_filtering import content_recommendation, train_transformer, transform_data
from scipy.sparse import load_npz
import pandas as pd
from numpy import load
from hybrid_recommendations import HybridRecommenderSystem
from pathlib import Path
import json
import requests
import os
from data_cleaning import data_for_content_filtering


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def _st_list_data_dir_and_stop(missing_path: Path):
    st.error(f"Data file not found: {missing_path}")
    st.write("Looking for data files in:", str(DATA_DIR))
    if DATA_DIR.exists() and DATA_DIR.is_dir():
        st.write("Files in `data/`:")
        for p in sorted(DATA_DIR.iterdir()):
            st.write("-", p.name)
    else:
        st.write("No `data/` directory found at", str(DATA_DIR))
    st.stop()

def _try_download_if_missing(path: Path) -> bool:
    """If a data_urls.json mapping exists, try to download the missing file.
    Returns True if file was downloaded successfully, False otherwise.
    """
    urls_file = DATA_DIR / "data_urls.json"
    if not urls_file.exists():
        return False

    try:
        mapping = json.loads(urls_file.read_text(encoding="utf-8"))
    except Exception:
        return False

    key = path.name
    url = mapping.get(key) or mapping.get(str(path))
    if not url:
        return False

    # Protect against placeholder/example URLs in data_urls.json
    if "example.com" in url or url.strip().upper() in ("PLACEHOLDER", "TBD", "TODO"):
        st.warning(f"Found placeholder download URL for `{key}` in data/data_urls.json; skipping download.")
        return False

    # If repository on deploy contains .dvc placeholders or Git LFS pointers,
    # avoid futile download attempts and surface clear guidance instead.
    if DATA_DIR.exists() and any(p.name.endswith('.dvc') for p in DATA_DIR.iterdir()):
        st.warning("Detected .dvc placeholder files in `data/` — raw data objects were not included in the repo on deploy.")
        st.write("Either enable Git LFS for your deployment (Streamlit Cloud supports Git LFS), or host the raw data externally and add real URLs to `data/data_urls.json`.")
        return False

    try:
        st.info(f"Attempting to download `{key}` from provided URL...")
        # Ensure data dir exists
        os.makedirs(path.parent, exist_ok=True)
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        st.success(f"Downloaded {key} to {path}")
        return True
    except Exception as e:
        st.warning(f"Failed to download {key}: {e}")
        return False

def _read_csv_rel(path: Path):
    # If file exists, ensure it's not a Git LFS pointer (pointer files are small text files)
    if path.exists():
        try:
            first_line = path.open('r', encoding='utf-8', errors='ignore').readline()
            if first_line.strip().startswith('version https://git-lfs.github.com/spec/v1'):
                st.error("A Git LFS pointer file was found for: " + str(path.name))
                st.write("This indicates the LFS object was not downloaded during deploy."
                         " Ensure your deployment source pulls Git LFS objects (Streamlit Cloud supports Git LFS),"
                         " or provide a direct download URL in `data/data_urls.json`.")
                st.write("Helpful steps:")
                st.write("- Confirm the Streamlit app is connected to the correct GitHub repo and branch.")
                st.write("- Re-deploy the app and choose 'Clear cache and redeploy' in Streamlit Cloud.")
                st.write("- Alternatively, host the data externally and add URLs to `data/data_urls.json`.")
                st.stop()
        except Exception:
            # if reading fails, fall through and let pandas raise a useful error
            pass

    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        # try to download if URL mapping provided, then retry
        if _try_download_if_missing(path):
            return pd.read_csv(path)
        _st_list_data_dir_and_stop(path)

def _load_npz_rel(path: Path):
    try:
        return load_npz(path)
    except FileNotFoundError:
        if _try_download_if_missing(path):
            return load_npz(path)
        _st_list_data_dir_and_stop(path)

def _np_load_rel(path: Path, **kwargs):
    try:
        return load(path, **kwargs)
    except FileNotFoundError:
        if _try_download_if_missing(path):
            return load(path, **kwargs)
        _st_list_data_dir_and_stop(path)

# load the data (paths resolved relative to this file)
cleaned_data_path = DATA_DIR / "cleaned_data.csv"
# prefer the full data; if missing on deploy, fall back to a small sample included in the repo
sample_cleaned = DATA_DIR / "cleaned_data_sample.csv"
if cleaned_data_path.exists():
    songs_data = _read_csv_rel(cleaned_data_path)
elif sample_cleaned.exists():
    st.warning("Full dataset not found — using bundled small sample for deployment.")
    songs_data = pd.read_csv(sample_cleaned)
else:
    songs_data = _read_csv_rel(cleaned_data_path)

# load or compute the transformed data (content-based)
transformed_data_path = DATA_DIR / "transformed_data.npz"
if transformed_data_path.exists():
    transformed_data = load_npz(transformed_data_path)
else:
    # Compute on the fly from available songs_data (works with sample too)
    try:
        st.warning("transformed_data.npz not found — computing content features on the fly (demo mode).")
        df_cf = data_for_content_filtering(songs_data.copy())
        # train transformer and transform data
        train_transformer(df_cf)
        transformed_data = transform_data(df_cf)
    except Exception as e:
        st.error(f"Unable to compute content features: {e}")
        _st_list_data_dir_and_stop(transformed_data_path)

# track ids are only required for hybrid mode; load conditionally below
track_ids = None

# Try to load hybrid/collaborative artifacts; if missing, disable hybrid mode gracefully
hybrid_available = True

filtered_data = None
filtered_data_path = DATA_DIR / "collab_filtered_data.csv"
if filtered_data_path.exists():
    filtered_data = _read_csv_rel(filtered_data_path)
else:
    hybrid_available = False

interaction_matrix = None
interaction_matrix_path = DATA_DIR / "interaction_matrix.npz"
if interaction_matrix_path.exists():
    interaction_matrix = load_npz(interaction_matrix_path)
else:
    hybrid_available = False

transformed_hybrid_data = None
transformed_hybrid_data_path = DATA_DIR / "transformed_hybrid_data.npz"
if transformed_hybrid_data_path.exists():
    transformed_hybrid_data = load_npz(transformed_hybrid_data_path)
else:
    hybrid_available = False

# load track ids only if present; otherwise disable hybrid
track_ids_path = DATA_DIR / "track_ids.npy"
if track_ids_path.exists():
    track_ids = _np_load_rel(track_ids_path, allow_pickle=True)
else:
    hybrid_available = False

# Title
st.title('Welcome to the Spotify Song Recommender!')

# Subheader
st.write('### Enter the name of a song and the recommender will suggest similar songs 🎵🎧')

# Text Input
song_name = st.text_input('Enter a song name:')
st.write('You entered:', song_name)
# artist name
artist_name = st.text_input('Enter the artist name:')
st.write('You entered:', artist_name)
# lowercase the input
song_name = song_name.lower()
artist_name = artist_name.lower()

# k recommndations
k = st.selectbox('How many recommendations do you want?', [5,10,15,20], index=1)

# Determine available mode and default filtering type
filtering_type = 'Content-Based Filtering'
if hybrid_available and filtered_data is not None:
    try:
        if ((filtered_data["name"] == song_name) & (filtered_data["artist"] == artist_name)).any():
            filtering_type = "Hybrid Recommender System"
    except Exception:
        filtering_type = 'Content-Based Filtering'

    # diversity slider
    diversity = st.slider(label="Diversity in Recommendations",
                        min_value=1,
                        max_value=9,
                        value=5,
                        step=1)

    content_based_weight = 1 - (diversity / 10)
    
    # plot a bar graph
    chart_data = pd.DataFrame({
        "type" : ["Personalized", "Diverse"],
        "ratio": [10 - diversity, diversity]
    })
    
    st.bar_chart(chart_data,x="type",y="ratio")
    
if not hybrid_available:
    st.info("Hybrid mode artifacts not found on deploy — running in content-based demo mode.")

# Button
if filtering_type == 'Content-Based Filtering':
    if st.button('Get Recommendations'):
        if ((songs_data["name"] == song_name) & (songs_data['artist'] == artist_name)).any():
            st.write('Recommendations for', f"**{song_name}** by **{artist_name}**")
            recommendations = content_recommendation(song_name=song_name,
                                                     artist_name=artist_name,
                                                     songs_data=songs_data,
                                                     transformed_data=transformed_data,
                                                     k=k)
            
            # Display Recommendations
            for ind , recommendation in recommendations.iterrows():
                song_name = recommendation['name'].title()
                artist_name = recommendation['artist'].title()
                
                if ind == 0:
                    st.markdown("## Currently Playing")
                    st.markdown(f"#### **{song_name}** by **{artist_name}**")
                    _url = str(recommendation.get('spotify_preview_url') or '').strip()
                    if _url and _url.lower() != 'nan':
                        st.audio(_url)
                    st.write('---')
                elif ind == 1:   
                    st.markdown("### Next Up 🎵")
                    st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                    _url = str(recommendation.get('spotify_preview_url') or '').strip()
                    if _url and _url.lower() != 'nan':
                        st.audio(_url)
                    st.write('---')
                else:
                    st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                    _url = str(recommendation.get('spotify_preview_url') or '').strip()
                    if _url and _url.lower() != 'nan':
                        st.audio(_url)
                    st.write('---')
        else:
            st.write(f"Sorry, we couldn't find {song_name} in our database. Please try another song.")
            
elif filtering_type == "Hybrid Recommender System" and hybrid_available:
    if st.button('Get Recommendations'):
        st.write('Recommendations for', f"**{song_name}** by **{artist_name}**")
        recommender = HybridRecommenderSystem(
                                                number_of_recommendations= k,
                                                weight_content_based= content_based_weight
                                                )
                                
        # get the recommendations
        recommendations = recommender.give_recommendations(song_name= song_name,
                                artist_name= artist_name,
                                songs_data= filtered_data,
                                transformed_matrix= transformed_hybrid_data,
                                track_ids= track_ids,
                                interaction_matrix= interaction_matrix)
        # Display Recommendations
        for ind , recommendation in recommendations.iterrows():
            song_name = recommendation['name'].title()
            artist_name = recommendation['artist'].title()
            
            if ind == 0:
                st.markdown("## Currently Playing")
                st.markdown(f"#### **{song_name}** by **{artist_name}**")
                _url = str(recommendation.get('spotify_preview_url') or '').strip()
                if _url and _url.lower() != 'nan':
                    st.audio(_url)
                st.write('---')
            elif ind == 1:   
                st.markdown("### Next Up 🎵")
                st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                _url = str(recommendation.get('spotify_preview_url') or '').strip()
                if _url and _url.lower() != 'nan':
                    st.audio(_url)
                st.write('---')
            else:
                st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                _url = str(recommendation.get('spotify_preview_url') or '').strip()
                if _url and _url.lower() != 'nan':
                    st.audio(_url)
                st.write('---')
elif filtering_type == "Hybrid Recommender System" and not hybrid_available:
    st.warning("Hybrid recommendations are unavailable in this deployment. Please provide hybrid artifacts or use content-based mode.")