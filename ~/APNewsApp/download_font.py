import requests
import os

def download_font():
    url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    filename = "NanumGothic.ttf"
    
    print(f"Downloading {filename}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Failed to download font: {e}")

if __name__ == "__main__":
    download_font()
