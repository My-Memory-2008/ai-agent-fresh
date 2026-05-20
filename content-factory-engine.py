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
# 3b. 🔥 AI OCR CHECKPOINT: USERNAME WATERMARK SCANNER & BLUR PATCHER
# ==========================================
print("👁️ Launching OCR text-vision scanner for creator username watermarks...")
import cv2
import pytesseract
from pytesseract import Output

CLEANED_SOURCE_VIDEO = "/kaggle/working/cleaned_source.mp4"
TRIMMED_VIDEO = "/kaggle/working/trimmed_source.mp4"
EXTRACTED_AUDIO = "/kaggle/working/original_audio.aac"

# Open the downloaded video to scan layout coordinates
cap = cv2.VideoCapture(output_path)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
sample_frames = [int(frame_count * 0.15), int(frame_count * 0.45), int(frame_count * 0.75)]

text_watermark_box = None
clean_username_target = username.lower().strip()

print(f"🕵️ Scanning frame grids for creator name text matching: '{clean_username_target}'")

for idx in sample_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if not ret: continue
    
    # Sharpen contrast vectors for the OCR engine using grayscale conversion
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Run full OCR positional word scanning passes
    ocr_data = pytesseract.image_to_data(gray_frame, output_type=Output.DICT)
    
    # Loop over every single text word block detected inside the image canvas
    for i in range(len(ocr_data['text'])):
        detected_word = str(ocr_data['text'][i]).lower().strip()
        
        # Check if the scanned word matches or contains the creator's account handle name
        if clean_username_target in detected_word or (len(detected_word) > 3 and detected_word in clean_username_target):
            x = ocr_data['left'][i]
            y = ocr_data['top'][i]
            w = ocr_data['width'][i]
            h = ocr_data['height'][i]
            
            # Add safety padding margins around the box coordinates to fully cover the text width
            text_watermark_box = (max(0, x-15), max(0, y-10), w+30, h+20)
            break
    if text_watermark_box: break
cap.release()

# If the creator's name text block was found, execute erasure loop
if text_watermark_box:
    x, y, w, h = text_watermark_box
    print(f"🎯 Creator Watermark Found! Pixels located -> X:{x}, Y:{y}, W:{w}, H:{h}")
    print("🧼 Applying spatial blur-mask patch filter over username region...")
    
    # Run FFmpeg's built-in delogo filter exclusively over the text coordinates box boundaries
    subprocess.run([
        "ffmpeg", "-y", "-i", output_path,
        "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}",
        "-c:a", "copy", CLEANED_SOURCE_VIDEO
    ], check=True, capture_output=True)
    
    PROCESSING_INPUT_VIDEO = CLEANED_SOURCE_VIDEO
    print("✅ Creator username watermark blurred out. Safe file passed forward.")
else:
    print("✨ Clean Check! No matching account name text signatures found on screen.")
    PROCESSING_INPUT_VIDEO = output_path

# ==========================================
# 4. DYNAMIC TRIMMING & INTERNAL STORAGE CAT SELECTION
# ==========================================
print("⚡ Processing internal video timeline assembly structures...")

def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

orig_duration = get_duration(PROCESSING_INPUT_VIDEO)
print(f"⏱️ Original Video Duration: {orig_duration:.2f}s")

# Calculate trimmed target duration (Cut off the last 4 seconds)
trim_target_duration = max(2.0, orig_duration - 4.0) 
print(f"✂️ Trimming source video to: {trim_target_duration:.2f}s")

# Trim the watermark-scrubbed source video using high-speed stream copying
subprocess.run([
    "ffmpeg", "-y", "-i", PROCESSING_INPUT_VIDEO, 
    "-t", str(trim_target_duration), 
    "-c:v", "copy", "-c:a", "copy", 
    TRIMMED_VIDEO
], check=True, capture_output=True)

# Extract the complete audio track out of the watermark-scrubbed path to map over the cat scene smoothly
print("🎵 Extracting the full original sound track...")
subprocess.run([
    "ffmpeg", "-y", "-i", PROCESSING_INPUT_VIDEO,
    "-vn", "-acodec", "copy",
    EXTRACTED_AUDIO
], check=True, capture_output=True)

# Randomly select a cat reaction file directly from your Kaggle Dataset input path
cat_dataset_dir = "/kaggle/input/cat-reactions-vault"

if os.path.exists(cat_dataset_dir):
    valid_clips = []
    for root, dirs, files in os.walk(cat_dataset_dir):
        for file in files:
            if file.endswith('.mp4'):
                valid_clips.append(os.path.join(root, file))
                
    if valid_clips:
        chosen_cat_file = random.choice(valid_clips)
    else:
        raise FileNotFoundError("❌ Error: No .mp4 video files detected inside your dataset directory!")
else:
    print("⚠️ Dataset directory not found. Using safety video fallback...")
    chosen_cat_file = PROCESSING_INPUT_VIDEO 

print(f"🐱 Selected Reaction Asset from Internal Storage: {chosen_cat_file}")

# ==========================================
# 5. GPU-ACCELERATED PROCEDURAL VISUAL EDITING STACK (PIXEL RE-ALIGNED)
# ==========================================
print("🎬 Aligning dimensions and rendering multi-layer canvas via NVIDIA NVENC GPU...")

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

# Dynamic Filtergraph Layout for Pixel Alignment:
# 1. Takes the trimmed source video and forces the wallpaper backdrop to 1080x1920 portrait size.
# 2. Scales the inner primary unmirrored core reel container to exactly 918x1632 layout dimensions (safely protects original captions).
# 3. Merges them together and locks the resolution dimensions container at exactly 1080x1920 with setsar=1.
# 4. Takes your Kaggle dataset cat clip and forces its aspect layout sizing directly to 1080x1920 with setsar=1.
# 5. Connects both tracks cleanly via 'concat=n=2:v=1:a=0' without throwing mismatched input channel parameter errors.
# 6. Layers transparent moving grain text patterns and burns your custom brand watermark label '@AWRAM' securely over the whole project.
filter_complex_string = (
    f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
    f"[0:v]scale=918:1632,{chosen_style}[main];"
    f"[bg][main]overlay=(W-w)/2:(H-h)/2,scale=1080:1920,setsar=1[processed_source];"
    f"[2:v]scale=1080:1920,setsar=1[processed_cat];"
    f"[processed_source][processed_cat]concat=n=2:v=1:a=0[merged_video];"
    f"[merged_video]noise=alls=7:allf=t+u[grained];"
    f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v]"
)

ffmpeg_cmd = [
    "ffmpeg", "-y", 
    "-hwaccel", "cuda", 
    "-i", TRIMMED_VIDEO,         # Input index 0: Trimmed source video file
    "-i", EXTRACTED_AUDIO,       # Input index 1: Full original sound track file
    "-i", chosen_cat_file,       # Input index 2: Mounted dataset cat video file
    "-filter_complex", filter_complex_string,
    "-map", "[v]", 
    "-map", "1:a",               # Map the original sound track smoothly across the video layout timeline
    "-c:v", "h264_nvenc",        # NVIDIA Hardware Acceleration GPU
    "-preset", "p4", 
    "-cq", "20", 
    "-c:a", "aac", 
    "-b:a", "128k",
    "-shortest",                 # Cut off extra audio if it exceeds the video execution length boundaries
    OUTPUT_VIDEO
]

res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ FFmpeg compilation crashed: {res.stderr}")
    raise RuntimeError("FFmpeg Dataset Timeline Assembly Failure")
print(f"🚀 GPU Render Complete! Video Compiled from Internal Dataset at: {OUTPUT_VIDEO}")



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
