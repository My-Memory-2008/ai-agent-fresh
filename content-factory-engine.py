# %% [code]
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
# 4 & 5. T4 GPU AUDIO EXTRACTION, SPEECH TRANSCRIPTION & SPEED-SYNC RENDERING
# ==========================================
print("🚀 Initiating dynamic dependency checks & audio extraction sequence...")
import subprocess
import sys
import os
import random
import asyncio

# 4a. Dynamic Dependency Injector (Ensures SpeechRecognition is installed on boot)
try:
    import speech_recognition as sr
except ImportError:
    print("-> speech_recognition package missing. Forcing local environment injection...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "SpeechRecognition"])
    import speech_recognition as sr
    print("✅ Package loaded successfully.")

# Define absolute workspace audio tracking paths
EXTRACTED_AUDIO_MP3 = "/kaggle/working/extracted_audio.mp3"
EXTRACTED_AUDIO_WAV = "/kaggle/working/extracted_audio.wav"
NEW_VOICEOVER = "/kaggle/working/new_ai_voiceover.wav"

# 4b. Extract the true audio track from the downloaded Reel via FFmpeg
print("-> Isolating original audio track matrix...")
subprocess.run(["ffmpeg", "-y", "-i", output_path, "-q:a", "0", "-map", "a", EXTRACTED_AUDIO_MP3], check=True, capture_output=True)

# Convert to standard uncompressed WAV format for the local transcription engine
subprocess.run(["ffmpeg", "-y", "-i", EXTRACTED_AUDIO_MP3, EXTRACTED_AUDIO_WAV], check=True, capture_output=True)

# 4c. Transcribe the original speech using local CPU execution (Bypasses CUDA bugs)
print("-> Initializing CPU speech-to-text transcription engine...")
recognizer = sr.Recognizer()
extracted_text = ""

try:
    with sr.AudioFile(EXTRACTED_AUDIO_WAV) as source:
        audio_data = recognizer.record(source)
        # Uses Google's free public web speech API gateway to extract exact words
        extracted_text = recognizer.recognize_google(audio_data)
    print(f"📝 SUCCESS! Transcribed original video script: \"{extracted_text}\"")
except Exception as e:
    print(f"⚠️ Speech API failed or audio was silent: {e}")
    # Fallback only if the original audio track cannot be transcribed
    extracted_text = "Check out this amazing video!"
    print(f"📋 Using safety text fallback: \"{extracted_text}\"")

# 4d. Run Edge-TTS natively to build the professional human voice file
print("-> Querying Edge-TTS cloud service for professional narration...")
sanitized_text = extracted_text.replace('"', '').replace("'", "").strip()
selected_voice = "en-US-ChristopherNeural"

async def generate_edge_voice():
    import edge_tts
    communicate = edge_tts.Communicate(sanitized_text, selected_voice)
    await communicate.save(NEW_VOICEOVER)

asyncio.run(generate_edge_voice())
print("✅ Professional Edge-TTS voice track generated.")

# 4e. DYNAMIC SPEED CALCULATION ENGINE
print("⚡ Calculating precise speed normalization adjustments...")

def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

# Fetch durations down to the millisecond
orig_duration = get_duration(output_path)
tts_duration = get_duration(NEW_VOICEOVER)

# Calculate exactly how much we need to speed up/slow down the TTS voice to match the video length
speed_factor = tts_duration / orig_duration

# FFmpeg atempo boundaries rules: Must stay between 0.5 and 2.0
if speed_factor < 0.5: speed_factor = 0.5
if speed_factor > 2.0: speed_factor = 2.0

print(f"⏱️ Original Video Duration: {orig_duration:.2f}s")
print(f"⏱️ Raw Voiceover Duration: {tts_duration:.2f}s")
print(f"⏩ Required Voiceover Speed Factor: {speed_factor:.2f}x")

# ==========================================
# 5. GPU-ACCELERATED PROCEDURAL VISUAL EDITING STACK
# ==========================================
print("🎬 Stacking randomized filters and rendering vertical layout via NVIDIA NVENC GPU...")

styles = [
    "eq=contrast=1.05:brightness=0.01:saturation=1.02:gamma=0.97",
    "curves=m='0/0 0.25/0.18 0.5/0.5 0.75/0.82 1/1':r='0/0 0.5/0.42 1/1':b='0/0 0.4/0.58 1/1'",
    "eq=contrast=0.95:brightness=0.02:saturation=0.92:gamma=1.04"
]
chosen_style = random.choice(styles)

effects = [
    "zoompan=z='min(zoom+0.003,1.12)':x='iw/2-iw/zoom/2+sin(time*2.5)*6':y='ih/2-ih/zoom/2':d=1",
    "convolution='-1 -1 -1 -1 9 -1 -1 -1 -1',eq=contrast=1.06:brightness=0.01",
    "hue='H=2.5*PI*t:s=1.03'"
]
chosen_effect = random.choice(effects)

# Setup 9:16 portrait layout canvas (Safe unmirrored captions + blurred backdrop wallpaper + transparent dust/grain noise + custom brand watermark)
filter_complex_string = (
    f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
    f"[0:v]scale=918:1632,{chosen_style}[main];"
    f"[bg][main]overlay=(W-w)/2:(H-h)/2[merged];"
    f"[merged]noise=alls=7:allf=t+u[grained];"
    f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v];"
    f"[1:a]atempo={speed_factor}[speed_synced_audio]"
)

# GPU ACCELERATION: Leverages NVIDIA NVENC T4 Hardware Video Encoder directly
ffmpeg_cmd = [
    "ffmpeg", "-y", 
    "-hwaccel", "cuda",         # Initialize CUDA hardware acceleration gates
    "-i", output_path,          # Original video matrix layout
    "-i", NEW_VOICEOVER,         # Raw Edge-TTS track
    "-filter_complex", filter_complex_string,
    "-map", "[v]", 
    "-map", "[speed_synced_audio]", # Map the speed-corrected narration track
    "-c:v", "h264_nvenc",       # Force NVIDIA NVENC Hardware Video Encoder GPU
    "-preset", "p4",            # High-performance hardware preset mapping
    "-cq", "20",                # Maintain perfect clarity for text and borders
    "-c:a", "aac",              
    "-b:a", "128k",
    "-shortest",                # Ensure no trailing dead space
    OUTPUT_VIDEO
]

res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ FFmpeg transformative execution crashed: {res.stderr}")
    raise RuntimeError("FFmpeg Pipeline Failure")
print(f"🚀 GPU Render Complete! Video Saved: {OUTPUT_VIDEO}")


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



# # ==========================================
# # 4 & 5. DATASET CAT REACTION STITCHING & GPU RENDERING
# # ==========================================
# print("🚀 Initiating high-speed Kaggle Dataset video compilation sequence...")
# import os
# import random
# import asyncio
# import subprocess

# # Define path configurations
# NEW_VOICEOVER = "/kaggle/working/new_ai_voiceover.wav"
# TRIMMED_VIDEO = "/kaggle/working/trimmed_source.mp4"

# # 4a. Read script text sent from your GitHub queue file
# extracted_text = pipeline.get("script_text", "Look at this mind-blowing tech hack!")
# sanitized_text = extracted_text.replace('"', '').replace("'", "").strip()

# # 4b. Run Edge-TTS natively to build the professional human voice file
# print("-> Querying Edge-TTS cloud service for professional narration...")
# selected_voice = "en-US-ChristopherNeural"

# async def generate_edge_voice():
#     import edge_tts
#     communicate = edge_tts.Communicate(sanitized_text, selected_voice)
#     await communicate.save(NEW_VOICEOVER)

# asyncio.run(generate_edge_voice())
# print("✅ Edge-TTS voice track successfully generated.")

# # 4c. DYNAMIC TRIMMING & INTERNAL STORAGE CAT SELECTION
# print("⚡ Processing internal video timeline assembly structures...")

# def get_duration(file_path):
#     cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
#     return float(subprocess.check_output(cmd, shell=True).decode().strip())

# orig_duration = get_duration(output_path)
# print(f"⏱️ Original Video Duration: {orig_duration:.2f}s")

# # Calculate trimmed target duration (Cut off the last 4 seconds)
# trim_target_duration = max(2.0, orig_duration - 4.0) 
# print(f"✂️ Trimming source video to: {trim_target_duration:.2f}s")

# # Trim the source video accurately using high-speed stream copying
# subprocess.run([
#     "ffmpeg", "-y", "-i", output_path, 
#     "-t", str(trim_target_duration), 
#     "-c:v", "copy", "-c:a", "copy", 
#     TRIMMED_VIDEO
# ], check=True, capture_output=True)

# # 4d. 🔥 NEW: Randomly select a cat reaction file directly from your Kaggle Dataset input path
# # Change 'cat-reactions-vault' to match your folder sub-directory name inside Kaggle Input
# cat_dataset_dir = "/kaggle/input/cat-reactions-vault"

# if os.path.exists(cat_dataset_dir) and os.listdir(cat_dataset_dir):
#     # Filter out hidden or non-video assets to isolate clean .mp4 files safely
#     valid_clips = [f for f in os.listdir(cat_dataset_dir) if f.endswith('.mp4')]
#     if valid_clips:
#         chosen_cat_file = os.path.join(cat_dataset_dir, random.choice(valid_clips))
#     else:
#         chosen_cat_file = os.path.join(cat_dataset_dir, random.choice(os.listdir(cat_dataset_dir)))
# else:
#     print("⚠️ Dataset empty or not mounted properly yet. Using safety video fallback...")
#     chosen_cat_file = output_path 

# print(f"🐱 Selected Reaction Asset from Internal Storage: {chosen_cat_file}")

# # 4e. SPEED FACTORS MEASUREMENTS
# tts_duration = get_duration(NEW_VOICEOVER)
# total_new_duration = trim_target_duration + 4.0 
# speed_factor = tts_duration / total_new_duration

# if speed_factor < 0.5: speed_factor = 0.5
# if speed_factor > 2.0: speed_factor = 2.0
# print(f"⏩ Required Voiceover Speed Factor: {speed_factor:.2f}x")

# # ==========================================
# # 5. GPU-ACCELERATED PROCEDURAL VISUAL EDITING STACK
# # ==========================================
# print("🎬 Merging tracks and rendering multi-layer canvas via NVIDIA NVENC GPU...")

# styles = [
#     "eq=contrast=1.05:brightness=0.01:saturation=1.02:gamma=0.97",
#     "curves=m='0/0 0.25/0.18 0.5/0.5 0.75/0.82 1/1':r='0/0 0.5/0.42 1/1':b='0/0 0.4/0.58 1/1'",
#     "eq=contrast=0.95:brightness=0.02:saturation=0.92:gamma=1.04"
# ]
# chosen_style = random.choice(styles)

# effects = [
#     "zoompan=z='min(zoom+0.003,1.12)':x='iw/2-iw/zoom/2+sin(time*2.5)*6':y='ih/2-ih/zoom/2':d=1",
#     "convolution='-1 -1 -1 -1 9 -1 -1 -1 -1',eq=contrast=1.06:brightness=0.01",
#     "hue='H=2.5*PI*t:s=1.03'"
# ]
# chosen_effect = random.choice(effects)

# # Construct 9:16 complex layout pipeline map:
# filter_complex_string = (
#     f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
#     f"[0:v]scale=918:1632,{chosen_style}[main];"
#     f"[bg][main]overlay=(W-w)/2:(H-h)/2[processed_source];"
#     f"[2:v]scale=1080:1920[processed_cat];"
#     f"[processed_source][processed_cat]concat=n=2:v=1:a=0[merged_video];"
#     f"[merged_video]noise=alls=7:allf=t+u[grained];"
#     f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v];"
#     f"[1:a]atempo={speed_factor}[speed_synced_audio]"
# )

# ffmpeg_cmd = [
#     "ffmpeg", "-y", 
#     "-hwaccel", "cuda", 
#     "-i", TRIMMED_VIDEO,         # Input index 0: Trimmed source video file
#     "-i", NEW_VOICEOVER,         # Input index 1: New Edge-TTS narrator audio file
#     "-i", chosen_cat_file,       # Input index 2: Mounted dataset cat video file
#     "-filter_complex", filter_complex_string,
#     "-map", "[v]", 
#     "-map", "[speed_synced_audio]", 
#     "-c:v", "h264_nvenc",       # NVIDIA Hardware Acceleration GPU
#     "-preset", "p4", 
#     "-cq", "20", 
#     "-c:a", "aac", 
#     "-b:a", "128k",
#     "-shortest",
#     OUTPUT_VIDEO
# ]

# res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
# if res.returncode != 0:
#     print(f"❌ FFmpeg compilation crashed: {res.stderr}")
#     raise RuntimeError("FFmpeg Dataset Timeline Assembly Failure")
# print(f"🚀 GPU Render Complete! Video Compiled from Internal Dataset at: {OUTPUT_VIDEO}")

