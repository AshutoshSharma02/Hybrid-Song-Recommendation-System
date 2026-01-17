import streamlit as st
from content_based_filtering import content_recommendation
from scipy.sparse import load_npz
import pandas as pd
from numpy import load
from hybrid_recommendations import HybridRecommenderSystem
from pathlib import Path
import json
import requests
import os


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
songs_data = _read_csv_rel(cleaned_data_path)

# load the transformed data
transformed_data_path = DATA_DIR / "transformed_data.npz"
transformed_data = _load_npz_rel(transformed_data_path)

# load the track ids
track_ids_path = DATA_DIR / "track_ids.npy"
track_ids = _np_load_rel(track_ids_path, allow_pickle=True)

# load the filtered songs data
filtered_data_path = DATA_DIR / "collab_filtered_data.csv"
filtered_data = _read_csv_rel(filtered_data_path)

# load the interaction matrix
interaction_matrix_path = DATA_DIR / "interaction_matrix.npz"
interaction_matrix = _load_npz_rel(interaction_matrix_path)

# load the transformed hybrid data
transformed_hybrid_data_path = DATA_DIR / "transformed_hybrid_data.npz"
transformed_hybrid_data = _load_npz_rel(transformed_hybrid_data_path)

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

if ((filtered_data["name"] == song_name) & (filtered_data["artist"] == artist_name)).any():   
    # type of filtering
    filtering_type = "Hybrid Recommender System"

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
    
else:
    # type of filtering
    filtering_type = 'Content-Based Filtering'

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
                    st.audio(recommendation['spotify_preview_url'])
                    st.write('---')
                elif ind == 1:   
                    st.markdown("### Next Up 🎵")
                    st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                    st.audio(recommendation['spotify_preview_url'])
                    st.write('---')
                else:
                    st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                    st.audio(recommendation['spotify_preview_url'])
                    st.write('---')
        else:
            st.write(f"Sorry, we couldn't find {song_name} in our database. Please try another song.")
            
elif filtering_type == "Hybrid Recommender System":
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
                st.audio(recommendation['spotify_preview_url'])
                st.write('---')
            elif ind == 1:   
                st.markdown("### Next Up 🎵")
                st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                st.audio(recommendation['spotify_preview_url'])
                st.write('---')
            else:
                st.markdown(f"#### {ind}. **{song_name}** by **{artist_name}**")
                st.audio(recommendation['spotify_preview_url'])
                st.write('---')