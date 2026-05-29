# %% [code]
import subprocess
import sys
subprocess.run("apt-get update -qq && apt-get install -y -qq ffmpeg > /dev/null", shell=True, check=True)

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
    "edge-tts"
]

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages)

print("✅ Dependencies installed. Ready for main script.")

#!/usr/bin/env python3
# production_pipeline.py
# Fully Automated YouTube Shorts Engine: Download → Visual Transformation → Upload → Ledger Update
import os, json, re, requests, subprocess, time, random, torch
from kaggle_secrets import UserSecretsClient
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ==========================================
# 1. CONFIG & SECRETS
# ==========================================
print("🔐 Loading environment & secrets...")
secrets = UserSecretsClient()
GH_TOKEN = secrets.get_secret("GH_TOKEN")
YT_CLIENT_ID = secrets.get_secret("YOUTUBE_CLIENT_ID")
YT_CLIENT_SECRET = secrets.get_secret("YOUTUBE_CLIENT_SECRET")
YT_REFRESH_TOKEN = secrets.get_secret("YOUTUBE_REFRESH_TOKEN")

GITHUB_USER = os.environ.get("GITHUB_USER", "My-Memory-2008")  # Auto-updates via env or default
GITHUB_REPO = "content-factory-orchestrator"
BRANCH = "main"

WORKING_DIR = "/kaggle/working"
RAW_DIR = os.path.join(WORKING_DIR, "raw_video")
PIPELINE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{BRANCH}/pipeline_data.json"
QUEUE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{BRANCH}/reel_queue.json"
OUTPUT_VIDEO = os.path.join(WORKING_DIR, "final_youtube_short.mp4")

os.makedirs(RAW_DIR, exist_ok=True)

# ==========================================
# 2. FETCH PIPELINE DATA
# ==========================================
print("🌐 Fetching pipeline_data.json...")
resp = requests.get(PIPELINE_URL, timeout=30)
resp.raise_for_status()
pipeline = resp.json()

reel_url = pipeline.get("reel_url")
shortcode = pipeline.get("shortcode")
username = pipeline.get("username", "unknown")
print(f"🎯 Target: {reel_url} | Shortcode: {shortcode}")

# ==========================================
# 3. DOWNLOAD REEL (Direct CDN + Fallback)
# ==========================================
print("📥 Downloading video...")
video_url = None
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-IG-App-ID": "936619743392459"
}

try:
    # Method 1: Instagram Public API
    resp = requests.get(f"https://www.instagram.com/api/v1/media/{shortcode}/?__a=1&__d=dis", headers=headers, timeout=30)
    if resp.status_code == 200 and 'items' in resp.json():
        video_url = resp.json()['items'][0].get('video_versions', [{}])[0].get('url')
except Exception as e:
    print(f"⚠️ API fetch failed: {e}")

# Method 2: Instaloader Fallback
if not video_url:
    import instaloader
    L = instaloader.Instaloader(download_videos=False, download_pictures=False)
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        video_url = post.video_url
    except Exception as e:
        raise RuntimeError(f"❌ All download methods failed: {e}")

print(f"⬇️ Downloading from CDN...")
v_resp = requests.get(video_url, stream=True, timeout=120)
v_resp.raise_for_status()
output_path = os.path.join(RAW_DIR, f"{username}_{shortcode}.mp4")
with open(output_path, 'wb') as f:
    for chunk in v_resp.iter_content(chunk_size=8192):
        if chunk: f.write(chunk)
print(f"✅ Downloaded: {os.path.basename(output_path)} ({os.path.getsize(output_path)//1024} KB)")


# ==========================================
# 4 & 5. FREEZE-PROOF TWO-STAGE GPU CONCAT COMPILER
# ==========================================
print("🚀 Initiating freeze-proof multi-video timeline assembly stack...")
import subprocess
import sys
import os
import random

# Define separate internal rendering layer file paths
EDITED_SOURCE_MP4 = "/kaggle/working/edited_source_only.mp4"
STANDARDIZED_CAT_MP4 = "/kaggle/working/standardized_cat.mp4"

def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

# ------------------------------------------
# STAGE 1: RENDER ORIGINAL VIDEO IN VERTICAL MATRIX
# ------------------------------------------
print("🎬 Stage 1: Applying 9:16 canvas transformations to original video...")

styles = [
    "eq=contrast=1.05:brightness=0.01:saturation=1.02:gamma=0.97",
    "curves=m='0/0 0.25/0.18 0.5/0.5 0.75/0.82 1/1'",
    "eq=contrast=0.95:brightness=0.02:saturation=0.92:gamma=1.04"
]
chosen_style = random.choice(styles)

effects = [
    "convolution='-1 -1 -1 -1 9 -1 -1 -1 -1',eq=contrast=1.06:brightness=0.01",
    "hue='H=0.1*PI*t:s=1.03'",
    "eq=contrast=1.1:brightness=0.02:saturation=1.05"
]
chosen_effect = random.choice(effects)

orig_duration = get_duration(output_path)
trim_target_duration = max(2.0, orig_duration - 4.0)
print(f"✂️ Trimming target source video timeline boundaries down to: {trim_target_duration:.2f}s")

# Setup vertical template container layout graph strings safely
filter_complex_stage1 = (
    f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
    f"[0:v]scale=918:1632,{chosen_style}[main_scaled];"
    f"[bg][main_scaled]overlay=(W-w)/2:(H-h)/2,setsar=1[processed_source];"
    f"[processed_source]noise=alls=7:allf=t+u[grained];"
    f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v]"
)

ffmpeg_stage1 = [
    "ffmpeg", "-y", "-hwaccel", "cuda", 
    "-i", output_path,          
    "-t", str(trim_target_duration), # Safely clips the timeline loop right inside Stage 1 processing
    "-filter_complex", filter_complex_stage1, 
    "-map", "[v]", "-map", "0:a?", 
    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", 
    "-c:a", "aac", "-b:a", "128k",
    EDITED_SOURCE_MP4
]

res1 = subprocess.run(ffmpeg_stage1, capture_output=True, text=True)
if res1.returncode != 0:
    print(f"❌ Stage 1 Render crashed: {res1.stderr}")
    raise RuntimeError("FFmpeg Stage 1 Failure")
print("✅ Stage 1 Complete: Vertical visual layouts processed successfully.")

# ------------------------------------------
# STAGE 2: SELECT AND STANDARDIZE CAT REACTION VIDEO FILE
# ------------------------------------------
cat_dataset_dir = "/kaggle/input/datasets/muhammadasjad2008/cat-reactions-vault"
if os.path.exists(cat_dataset_dir):
    valid_clips = [os.path.join(root, f) for root, _, files in os.walk(cat_dataset_dir) for f in files if f.endswith('.mp4')]
    chosen_cat_file = random.choice(valid_clips) if valid_clips else output_path
else:
    chosen_cat_file = output_path
print(f"🐱 Selected Cat Reaction Asset: {chosen_cat_file}")

print("⚙️ Stage 2: Standardizing cat video dimensions and padding silent audio...")
# Fixes freezes by forcing the cat clip to match your edited video resolution and creating a silent audio stream
ffmpeg_stage2 = [
    "ffmpeg", "-y", "-hwaccel", "cuda",
    "-i", chosen_cat_file,
    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", 
    "-filter_complex", "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v]",
    "-map", "[v]", "-map", "1:a", 
    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20",
    "-c:a", "aac", "-b:a", "128k", "-shortest",
    STANDARDIZED_CAT_MP4
]

res2 = subprocess.run(ffmpeg_stage2, capture_output=True, text=True)
if res2.returncode != 0:
    print(f"❌ Stage 2 Audio/Video Standardization crashed: {res2.stderr}")
    raise RuntimeError("FFmpeg Stage 2 Failure")

# ------------------------------------------
# STAGE 3: MERGE EDITED VIDEO + CAT PUNCHLINE LIVE
# ------------------------------------------
print("🤝 Stage 3: Merging video timelines directly via rapid stream copy container links...")

concat_list_path = "/kaggle/working/concat_list.txt"
with open(concat_list_path, "w") as f:
    f.write(f"file '{EDITED_SOURCE_MP4}'\n")
    f.write(f"file '{STANDARDIZED_CAT_MP4}'\n")

# Rapid non-transcoded copy merge takes under 0.5 seconds because parameters match perfectly
ffmpeg_stage3 = [
    "ffmpeg", "-y",
    "-f", "concat", "-safe", "0",
    "-i", concat_list_path,
    "-c", "copy", 
    OUTPUT_VIDEO
]

res3 = subprocess.run(ffmpeg_stage3, capture_output=True, text=True)
if res3.returncode != 0:
    print(f"❌ Stage 3 Concat Link execution crashed: {res3.stderr}")
    raise RuntimeError("FFmpeg Stage 3 Failure")

print(f"🎉 SUCCESS! Fully compiled video ready for publication: {OUTPUT_VIDEO}")




# ==========================================
# 5. UPLOAD TO YOUTUBE
# ==========================================
print("📤 Uploading to YouTube...")
yt_url = None
upload_success = False
try:
    creds = Credentials(token=None, refresh_token=YT_REFRESH_TOKEN,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET,
                        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    if creds.expired: creds.refresh(Request())
    
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": pipeline.get("youtube_title", "AI Tip #shorts"),
                    "description": pipeline.get("youtube_description", ""),
                    "tags": pipeline.get("youtube_tags", ["AI", "Shorts"])},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=MediaFileUpload(OUTPUT_VIDEO, chunksize=-1, resumable=True))
    response = request.execute()
    yt_url = f"https://www.youtube.com/watch?v={response['id']}"
    upload_success = True
    print(f"🎉 YouTube Success: {yt_url}")
except Exception as e:
    print(f"⚠️ Upload failed (video saved locally): {e}")

# ==========================================
# 6. UPDATE GITHUB LEDGER
# ==========================================
print("🔄 Updating GitHub ledger...")
try:
    led_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/reel_queue.json"
    headers_gh = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp_gh = requests.get(led_url, headers=headers_gh)
    current = json.loads(requests.utils.b64decode(resp_gh.json()["content"]).decode())
    
    # Safely convert time formats
    from datetime import datetime, timezone
    
    for entry in current.get('processed', []):
        if entry['url'] == reel_url and entry.get('status') == 'in_progress':
            entry['status'] = 'success' if upload_success else 'failed'
            if yt_url: entry['youtube_url'] = yt_url
            entry['completed_at'] = datetime.now(timezone.utc).isoformat()
            break
            
    new_content = requests.utils.b64encode(json.dumps(current).encode()).decode()
    requests.put(led_url, headers=headers_gh, json={"message": "Auto: Updated reel status", "content": new_content, "sha": resp_gh.json()["sha"]})
    print("✅ Ledger updated.")
except Exception as e:
    print(f"⚠️ Ledger warning: {e}")

print("\n🏆 PIPELINE COMPLETE!")