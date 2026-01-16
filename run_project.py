"""
Complete setup and run script for Spotify Recommender System
This script will:
1. Download data from Kaggle
2. Process the data through the pipeline
3. Launch the Streamlit app
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
    if result.returncode == 0:
        print(f"[OK] {description} completed successfully")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"[ERROR] {description} failed")
        print(result.stderr)
        return False
    return True

def main():
    # Get Python executable from virtual environment
    venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    
    # Step 1: Download and setup data
    if not run_command(f'"{venv_python}" setup_data.py', "Downloading and copying data"):
        print("\nFailed to download data. Exiting...")
        return
    
    # Check if data files exist
    data_path = Path(__file__).parent / "data"
    if not (data_path / "Music Info.csv").exists():
        print("\n[ERROR] Music Info.csv not found. Please check the download.")
        return
    
    # Step 2: Data cleaning
    if not run_command(f'"{venv_python}" data_cleaning.py', "Data cleaning"):
        print("\nData cleaning failed. Exiting...")
        return
    
    # Step 3: Content-based filtering (transforms data)
    if not run_command(f'"{venv_python}" content_based_filtering.py', "Content-based filtering"):
        print("\nContent-based filtering failed. Exiting...")
        return
    
    # Step 4: Collaborative filtering
    if not run_command(f'"{venv_python}" collaborative_filtering.py', "Collaborative filtering"):
        print("\nCollaborative filtering failed. Exiting...")
        return
    
    # Step 5: Transform filtered data
    if not run_command(f'"{venv_python}" transform_filtered_data.py', "Transforming filtered data"):
        print("\nData transformation failed. Exiting...")
        return
    
    print("\n" + "="*60)
    print("[SUCCESS] ALL PROCESSING COMPLETE!")
    print("="*60)
    print("\nStarting Streamlit app...")
    print("The app will open in your browser at http://localhost:8501")
    print("Press Ctrl+C to stop the server\n")
    
    # Step 6: Launch Streamlit app
    subprocess.run(f'"{venv_python}" -m streamlit run app.py', shell=True)

if __name__ == "__main__":
    main()
