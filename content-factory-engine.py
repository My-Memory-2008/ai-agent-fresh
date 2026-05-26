# %% [code]
import subprocess
import sys
import os
import json
import re
import requests
import time
import random
import torch
import asyncio

# ==========================================
# SYSTEM DEPENDENCIES & PACKAGES INSTALLATION
# ==========================================
print("🔄 Installing core system binaries and pip packages...")
subprocess.run("apt-get update -qq && apt-get install -y -qq ffmpeg tesseract-ocr > /dev/null", shell=True, check=True)

packages = [
    "requests",
    "torch",
    "transformers",
    "scipy",
    "accelerate",
    "google-api-python-client",
    "google-auth-oauthlib",
    "google-auth-httplib2",
    "instaloader",
    "edge-tts",
    "pytesseract",
    "groq",
    "SpeechRecognition"
]

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages)
print("✅ All dependencies injected. Ready for script runtime.")

#!/usr/bin/env python3
# production_pipeline.py

# ==========================================
# 1. CONFIG & SECRETS INITIALIZATION
# ==========================================
print("🔐 Loading environment & secrets...")
from kaggle_secrets import UserSecretsClient
secrets = UserSecretsClient()
GH_TOKEN = secrets.get_secret("GH_TOKEN")
YT_CLIENT_ID = secrets.get_secret("YOUTUBE_CLIENT_ID")
YT_CLIENT_SECRET = secrets.get_secret("YOUTUBE_CLIENT_SECRET")
YT_REFRESH_TOKEN = secrets.get_secret("YOUTUBE_REFRESH_TOKEN")

GITHUB_USER = os.environ.get("GITHUB_USER", "My-Memory-2008").strip()
GITHUB_REPO = "content-factory-orchestrator"
BRANCH = "main"

WORKING_DIR = "/kaggle/working"
RAW_DIR = os.path.join(WORKING_DIR, "raw_video")
OUTPUT_VIDEO = os.path.join(WORKING_DIR, "final_youtube_short.mp4")

CLEANED_SOURCE_VIDEO = "/kaggle/working/cleaned_source.mp4"
TRIMMED_VIDEO = "/kaggle/working/trimmed_source.mp4"
EXTRACTED_AUDIO = "/kaggle/working/original_audio.aac"
NEW_VOICEOVER_MP3 = "/kaggle/working/new_ai_voiceover.mp3"
SEO_MANIFEST_PATH = "/kaggle/working/seo_metadata.json"

# Audio extraction workspace variables
EXTRACTED_AUDIO_MP3 = "/kaggle/working/extracted_audio.mp3"
EXTRACTED_AUDIO_WAV = "/kaggle/working/extracted_audio.wav"

os.makedirs(RAW_DIR, exist_ok=True)

# ==========================================
# 2. FETCH PIPELINE DATA
# ==========================================
print("🌐 Fetching pipeline_data.json...")
# FIXED: Explicit slashes applied across repo mapping endpoints
PIPELINE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{BRANCH}/pipeline_data.json"
QUEUE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{BRANCH}/reel_queue.json"

resp = requests.get(PIPELINE_URL, timeout=30)
resp.raise_for_status()
pipeline = resp.json()

reel_url = pipeline.get("reel_url", "")
username = pipeline.get("username", "unknown")

# FIXED: Upgraded regex scanner to handle grid posts (/p/) and reels (/reel/) format link schemes cleanly
shortcode_match = re.search(r'/(?:reel|p)/([^/?]+)', reel_url)
shortcode = shortcode_match.group(1) if shortcode_match else pipeline.get("shortcode")

print(f"🎯 Target: {reel_url} | Extracted Shortcode: {shortcode} | Channel: @{username}")

if not shortcode or shortcode == "unknown":
    raise ValueError("❌ Link Schema Fault: Failed to parse shortcode layout string parameters.")

# ==========================================
# 3. DOWNLOAD REEL (Your Verified CDN Chassis)
# ==========================================
print("📥 Downloading video file layers from CDN...")
video_url = None
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-IG-App-ID": "936619743392459"
}

try:
    resp = requests.get(f"https://www.instagram.com/api/v1/media/{shortcode}/?__a=1&__d=dis", headers=headers, timeout=30)
    if resp.status_code == 200 and 'items' in resp.json():
        video_url = resp.json()['items'][0].get('video_versions', [{}])[0].get('url')
except Exception as e:
    print(f"⚠️ API fetch loop connection bypass: {e}")

if not video_url:
    import instaloader
    L = instaloader.Instaloader(download_videos=False, download_pictures=False)
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        video_url = post.video_url
    except Exception as e:
        raise RuntimeError(f"❌ All download methods failed to reach streaming endpoints: {e}")

print(f"⬇️ Downloading video binary assets directly from verified CDN endpoint...")
v_resp = requests.get(video_url, stream=True, timeout=120)
v_resp.raise_for_status()
output_path = os.path.join(RAW_DIR, f"{username}_{shortcode}.mp4")
with open(output_path, 'wb') as f:
    for chunk in v_resp.iter_content(chunk_size=8192):
        if chunk: f.write(chunk)
print(f"✅ Target content packet written successfully: {os.path.basename(output_path)} ({os.path.getsize(output_path)//1024} KB)")
