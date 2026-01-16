"""
Script to download and setup data for the Spotify Recommender System
"""
import kagglehub
import shutil
from pathlib import Path

# Download dataset
print("Downloading dataset from Kaggle...")
dataset_path = kagglehub.dataset_download('undefinenull/million-song-dataset-spotify-lastfm')
print(f"Dataset downloaded to: {dataset_path}")

# Setup paths
source_path = Path(dataset_path)
target_path = Path(__file__).parent / "data"

# Copy files
print("\nCopying files to data folder...")
files_to_copy = ['Music Info.csv', 'User Listening History.csv']

for file in files_to_copy:
    source_file = source_path / file
    target_file = target_path / file
    
    if source_file.exists():
        print(f"Copying {file}...")
        shutil.copy2(source_file, target_file)
        print(f"[OK] {file} copied successfully")
    else:
        print(f"[ERROR] {file} not found in downloaded dataset")

print("\n[OK] Data setup complete!")
print("\nNext steps:")
print("1. Run the data processing pipeline:")
print("   python data_cleaning.py")
print("   python content_based_filtering.py")
print("   python collaborative_filtering.py")
print("   python transform_filtered_data.py")
print("\n2. Start the Streamlit app:")
print("   streamlit run app.py")
