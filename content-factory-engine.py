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
# 4. AUDIO GENERATION: NATIVE EDGE-TTS CLOUD NARRATOR
# ==========================================
print("🎙️ Initiating Edge-TTS custom voiceover transformation sequence...")
import torch
import librosa
import asyncio
from transformers import WhisperProcessor, WhisperForConditionalGeneration

device = "cuda" if torch.cuda.is_available() else "cpu"

# Define absolute workspace audio tracking paths
EXTRACTED_AUDIO = "/kaggle/working/extracted_audio.wav"
NEW_VOICEOVER = "/kaggle/working/new_ai_voiceover.wav"

# 4a. Isolate and extract clean 16kHz mono audio from the downloaded Reel via FFmpeg
print("-> Isolating original audio track matrix...")
subprocess.run(["ffmpeg", "-y", "-i", output_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", EXTRACTED_AUDIO], check=True, capture_output=True)

# 4b. Load Native Whisper model directly to convert original speech into clean script text
print("-> Loading Native OpenAI Whisper for safe speech transcription...")
whisper_model_id = "openai/whisper-tiny.en"
whisper_processor = WhisperProcessor.from_pretrained(whisper_model_id)
whisper_model = WhisperForConditionalGeneration.from_pretrained(whisper_model_id).to(device)

# Load the audio file arrays using librosa to prevent missing frame errors
audio_input, sampling_rate = librosa.load(EXTRACTED_AUDIO, sr=16000)
input_features = whisper_processor(audio_input, sampling_rate=sampling_rate, return_tensors="pt").input_features.to(device)

# Generate transcribed token arrays via GPU
predicted_ids = whisper_model.generate(input_features)
extracted_text = whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
print(f"📝 Extracted Script text content: \"{extracted_text}\"")

# Clear Whisper from VRAM to prevent memory conflicts during video rendering stages
del whisper_model, whisper_processor, input_features, predicted_ids; torch.cuda.empty_cache()

# 4c. Run Edge-TTS natively to build the professional human voice file
print("-> Querying Edge-TTS cloud service for professional narration...")

# Clean text from quotes or characters that could break parsing parameters
sanitized_text = extracted_text.replace('"', '').replace("'", "").strip()

# Select your custom narrator profile here:
# Male Voices: 'en-US-ChristopherNeural', 'en-US-EricNeural', 'en-GB-RyanNeural'
# Female Voices: 'en-US-JennyNeural', 'en-US-MichelleNeural'
selected_voice = "en-US-ChristopherNeural"

async def generate_edge_voice():
    import edge_tts
    communicate = edge_tts.Communicate(sanitized_text, selected_voice)
    await communicate.save(NEW_VOICEOVER)

# Execute the asynchronous generator natively within Python's running thread
asyncio.run(generate_edge_voice())
print("✅ Professional custom narrator voiceover file successfully generated.")


# ==========================================
# 4. RANDOMIZED TRANSFORMATIVE RENDERING (Safe Unmirrored Captions + Effects)
# ==========================================
print("🎬 Setting up randomized filters and effects engines...")

# Style Filters Matrix (NO MIRRORING - Captions remain perfectly readable left-to-right)
styles = [
    # Style A: Clean & Minimal (Crisp contrast highlights, balanced white mappings)
    "eq=contrast=1.05:brightness=0.01:saturation=1.02:gamma=0.97",
    # Style B: Cyber/Tech (Cyan tints, matrix neon enhancements via map curves)
    "curves=m='0/0 0.25/0.18 0.5/0.5 0.75/0.82 1/1':r='0/0 0.5/0.42 1/1':b='0/0 0.4/0.58 1/1'",
    # Style C: Retro Film (Warm organic grading curves, subtle low-fidelity black points)
    "eq=contrast=0.95:brightness=0.02:saturation=0.92:gamma=1.04"
]
chosen_style = random.choice(styles)

# Transition Overlay Effects Matrix
effects = [
    # Effect A: Whip Pan / Dynamic Positional Zoom Bounce
    "zoompan=z='min(zoom+0.003,1.12)':x='iw/2-iw/zoom/2+sin(time*2.5)*6':y='ih/2-ih/zoom/2':d=1",
    # Effect B: Text Pop-up with Edge Shimmering Glow Matrix (Slight sharpening convolution filter)
    "convolution='-1 -1 -1 -1 9 -1 -1 -1 -1',eq=contrast=1.06:brightness=0.01",
    # Effect C: Vintage Light Leaks / Chemical Film Burn Color Shifting Cycles
    "hue='H=2.5*PI*t:s=1.03'"
]
chosen_effect = random.choice(effects)

print(f"🎨 Selected Visual Filter Style: {chosen_style}")
print(f"⚡ Injected Animation Effect Layer: {chosen_effect}")

# Construct 9:16 Architecture Pipeline (Unmirrored Zoom-Out + Blurred Backdrop Wrapper):
# 1. [0:v]scale=1080:1920,boxblur=25:5 -> Force full vertical backdrop frame, heavily blurred to serve as shifting wallpaper.
# 2. [0:v]scale=918:1632 -> Shrink original video layout to exactly 85%. This ZOOMS OUT the core file so text boundaries remain safe from clipping.
# 3. noise=alls=7:allf=t+u -> Layers an unnoticeable, moving frame-by-frame transparent dust/grain hash over everything.
# 4. drawtext -> Solidifies your custom '@AWRAM' protection monetization signature overlay watermark block.
filter_complex_string = (
    f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
    f"[0:v]scale=918:1632,{chosen_style}[main];"
    f"[bg][main]overlay=(W-w)/2:(H-h)/2[merged];"
    f"[merged]noise=alls=7:allf=t+u[grained];"
    f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v]"
)

ffmpeg_cmd = [
    "ffmpeg", "-y", 
    "-i", output_path,          # Input index 0: Original video layout 
    "-i", NEW_VOICEOVER,         # Input index 1: New Edge-TTS narrator track file
    "-filter_complex", filter_complex_string,
    "-map", "[v]", 
    "-map", "1:a",              # Map the new custom AI voiceover audio track completely overwriting original sound
    "-c:v", "libx264", 
    "-preset", "faster", 
    "-crf", "18", 
    "-c:a", "aac",              # Re-encode clean audio signature track profiles
    "-b:a", "128k",
    "-shortest",                # Clamp timeline clip boundaries to match the script execution length
    OUTPUT_VIDEO
]


res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ FFmpeg compilation crashed: {res.stderr}")
    raise RuntimeError("FFmpeg Procedural Execution Failure")
print(f"✅ 10x Transformed Vertical Shorts Video Rendered: {OUTPUT_VIDEO}")

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