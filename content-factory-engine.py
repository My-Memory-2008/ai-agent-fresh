# %% [code]
import subprocess
import sys
# Added tesseract-ocr system installation package directly onto your base dependency cell
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
    "pytesseract", # Injected core OCR dependency
    "groq"          # Injected official Groq SDK dependency
]

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages)
print("✅ Dependencies installed. Ready for main script.")

#!/usr/bin/env python3
# production_pipeline.py
# Fully Automated YouTube Shorts Engine: Download → Visual Transformation → Upload → Ledger Update
import os, json, re, requests, subprocess, time, random, torch, asyncio
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

GITHUB_USER = os.environ.get("GITHUB_USER", "My-Memory-2008") 
GITHUB_REPO = "content-factory-orchestrator"
BRANCH = "main"

WORKING_DIR = "/kaggle/working"
RAW_DIR = os.path.join(WORKING_DIR, "raw_video")
PIPELINE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{BRANCH}/pipeline_data.json"
QUEUE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{BRANCH}/reel_queue.json"
OUTPUT_VIDEO = os.path.join(WORKING_DIR, "final_youtube_short.mp4")

# Added verified timeline tracking files
CLEANED_SOURCE_VIDEO = "/kaggle/working/cleaned_source.mp4"
TRIMMED_VIDEO = "/kaggle/working/trimmed_source.mp4"
EXTRACTED_AUDIO = "/kaggle/working/original_audio.aac"
NEW_VOICEOVER_MP3 = "/kaggle/working/new_ai_voiceover.mp3"
SEO_MANIFEST_PATH = "/kaggle/working/seo_metadata.json"

os.makedirs(RAW_DIR, exist_ok=True)

# ==========================================
# 2. FETCH PIPELINE DATA
# ==========================================
print("🌐 Fetching pipeline_data.json...")
resp = requests.get(PIPELINE_URL, timeout=30)
resp.raise_for_status()
pipeline = resp.json()

reel_url = pipeline.get("reel_url", "")
username = pipeline.get("username", "unknown")

# Upgraded regex scanner to handle grid posts (/p/) and reels (/reel/) format link schemes cleanly
shortcode_match = re.search(r'/(?:reel|p)/([^/?]+)', reel_url)
shortcode = shortcode_match.group(1) if shortcode_match else pipeline.get("shortcode")

print(f"🎯 Target: {reel_url} | Shortcode: {shortcode} | Channel: @{username}")

if not shortcode or shortcode == "unknown":
    raise ValueError("❌ Link Schema Fault: Failed to parse shortcode layout string parameters.")

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
# 3b. IN-KAGGLE LLAMA 3.3 SATISFYING COMMENTARY SYSTEM
# ==========================================
print("🧠 Activating local text matrix analysis engine via Groq SDK...")
groq_key = secrets.get_secret("GROQ_API_KEY")

# Safe default fallback templates to insulate pipeline runs from API timeouts
seo_metadata = {
    "title": "Most Oddly Satisfying ASMR Challenge! 🤯 #shorts",
    "description": "Wait till the end for the funny cat reaction loop! Original concept inspired by creator. #shorts #asmr",
    "tags": ["satisfying", "asmr", "shorts", "relaxing"]
}
transformative_commentary_script = "I am completely convinced that watching this precision layout should be a full time job. The absolute execution of this cut scored a perfect ten out of ten. Stick around for the ending, because that drop is purely therapeutic."

if groq_key:
    try:
        from groq import Groq
        client = Groq(api_key=groq_key.strip())
        
        seo_prompt = (
            f"You are a viral YouTube Shorts creator specializing in Oddly Satisfying and ASMR commentary. "
            f"A video clip by @{username} is being heavily edited with video filters and finishes with a random funny cat reaction punchline.\n\n"
            f"Tasks:\n"
            f"1. SCRIPT_TEXT: Write a fast-paced, highly engaging 14-second human-like commentary (Max 40 words). "
            f"Use a relatable, humorous tone or a satisfying rating scale. Focus on why the video is mesmerizing, "
            f"hype up the precision of the clip, and explicitly tell viewers to stick around for the surprise cat reaction loop at the very end. "
            f"Example style: 'I am completely convinced that watching kinetic sand slicing should be a full-time profession. The absolute precision of this cut scored a perfect ten out of ten. Stick around for the ending, because that drop is purely therapeutic.'\n"
            f"2. YOUTUBE_TITLE: Write a clickable title (Max 70 chars) focusing entirely on the satisfying value. End strictly with #shorts.\n"
            f"3. YOUTUBE_DESCRIPTION: Write an engaging 3-sentence description. Sentence 1 is a witty comment about the loop or the cat at the end. "
            f"Sentence 2 states why this ASMR content is addictive. Sentence 3 is a CTA to subscribe. Include: \"Original concept inspired by @{username}\". Append hashtags.\n"
            f"4. YOUTUBE_TAGS: Provide an array of 6 trending keywords.\n\n"
            f"Return response STRICTLY as a raw JSON object with keys 'script_text', 'youtube_title', 'youtube_description', and 'youtube_tags'. Do not include markdown ticks."
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an advanced YouTube SEO optimizer that outputs raw JSON text data."},
                {"role": "user", "content": seo_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=350
        )
        
        # FIXED GROQ CHOICES INDEX: Employs explicit list index to safely grab content
        clean_json_text = chat_completion.choices[0].message.content.strip().replace('```json', '').replace('```', '').strip()
        ai_seo_data = json.loads(clean_json_text)
        
        transformative_commentary_script = ai_seo_data.get('script_text', transformative_commentary_script)
        seo_metadata = {
            "title": ai_seo_data.get('youtube_title', seo_metadata["title"]),
            "description": ai_seo_data.get('youtube_description', seo_metadata["description"]),
            "tags": ai_seo_data.get('youtube_tags', seo_metadata["tags"])
        }
        print(f"🎉 Transformative Commentary Generated: \"{transformative_commentary_script}\"")
    except Exception as e:
        print(f"⚠️ Groq engine fallback sequence triggered: {e}")

with open(SEO_MANIFEST_PATH, 'w') as f:
    json.dump(seo_metadata, f, indent=2)

# ==========================================
# 4b. AI OCR CHECKPOINT: USERNAME WATERMARK REMOVER
# ==========================================
print("👁️ Scanning frame layers for creator username text signatures...")

# FORCED MEMORY PURGE: Clean background scraper footprints before launching heavy GPU render steps
import gc
try:
    if 'L' in locals(): del L
    if 'post' in locals(): del post
except Exception:
    pass
gc.collect()
torch.cuda.empty_cache()

import cv2
import pytesseract
from pytesseract import Output

cap = cv2.VideoCapture(output_path)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
sample_frames = [int(frame_count * 0.15), int(frame_count * 0.45), int(frame_count * 0.75)]
text_watermark_box = None
clean_username_target = username.lower().strip()

for idx in sample_frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if not ret: continue
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ocr_data = pytesseract.image_to_data(gray_frame, output_type=Output.DICT)
    
    for i in range(len(ocr_data['text'])):
        detected_word = str(ocr_data['text'][i]).lower().strip()
        if clean_username_target in detected_word or (len(detected_word) > 3 and detected_word in clean_username_target):
            x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
            text_watermark_box = (max(0, x-15), max(0, y-10), w+30, h+20)
            break
    if text_watermark_box: break
cap.release()

if text_watermark_box:
    x, y, w, h = text_watermark_box
    print(f"🎯 Watermark Matched! Scrubbing region -> X:{x}, Y:{y}, W:{w}, H:{h}")
    subprocess.run(["ffmpeg", "-y", "-i", output_path, "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}", "-c:a", "copy", CLEANED_SOURCE_VIDEO], check=True, capture_output=True)
    PROCESSING_INPUT_VIDEO = CLEANED_SOURCE_VIDEO
else:
    print("✨ Clean Layout Check! Bypassing OCR erasure step.")
    PROCESSING_INPUT_VIDEO = output_path

# ==========================================
# 4c. NATIVE AUDIO GENERATION & TIMELINE TRIMMING
# ==========================================
def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

print("✂️ Trimming source video clip timeline...")
orig_duration = get_duration(PROCESSING_INPUT_VIDEO)
trim_target_duration = max(2.0, orig_duration - 4.0) 
print(f"⏱️ Target source length restricted down to: {trim_target_duration:.2f}s")

subprocess.run(["ffmpeg", "-y", "-i", PROCESSING_INPUT_VIDEO, "-t", str(trim_target_duration), "-c:v", "copy", "-c:a", "copy", TRIMMED_VIDEO], check=True, capture_output=True)

print("🎙️ Querying Edge-TTS system infrastructure...")
async def generate_edge_voice():
    import edge_tts
    communicate = edge_tts.Communicate(transformative_commentary_script, "en-US-ChristopherNeural")
    await communicate.save(NEW_VOICEOVER_MP3)

if os.path.exists(NEW_VOICEOVER_MP3): os.remove(NEW_VOICEOVER_MP3)
asyncio.run(generate_edge_voice())

while not os.path.exists(NEW_VOICEOVER_MP3) or os.path.getsize(NEW_VOICEOVER_MP3) == 0:
    time.sleep(0.5)
print("✅ High-fidelity custom narrator voice track saved successfully.")

# ==========================================
# 4d. DATASET REACTION LOADER & AUTOMATED SPEED SYNC
# ==========================================
cat_dataset_dir = "/kaggle/input/cat-reactions-vault"
if os.path.exists(cat_dataset_dir):
    valid_clips = [os.path.join(root, f) for root, _, files in os.walk(cat_dataset_dir) for f in files if f.endswith('.mp4')]
    chosen_cat_file = random.choice(valid_clips) if valid_clips else PROCESSING_INPUT_VIDEO
else:
    chosen_cat_file = PROCESSING_INPUT_VIDEO
print(f"🐱 Selected Cat Reaction Asset: {chosen_cat_file}")

tts_duration = get_duration(NEW_VOICEOVER_MP3)
total_new_duration = trim_target_duration + 4.0 
speed_factor = tts_duration / total_new_duration
if speed_factor < 0.5: speed_factor = 0.5
if speed_factor > 2.0: speed_factor = 2.0
print(f"⏩ Speed-sync Factor: {speed_factor:.2f}x")

# ==========================================
# 5. FAST GPU RENDERING STACK (ZOOMPAN REMOVED TO PREVENT FREEZE)
# ==========================================
print("🎬 Rendering multi-layer canvas via NVIDIA NVENC GPU...")
styles = [
    "eq=contrast=1.05:brightness=0.01:saturation=1.02:gamma=0.97",
    "curves=m='0/0 0.25/0.18 0.5/0.5 0.75/0.82 1/1'",
    "eq=contrast=0.95:brightness=0.02:saturation=0.92:gamma=1.04"
]
effects = [
    "convolution='-1 -1 -1 -1 9 -1 -1 -1 -1',eq=contrast=1.06:brightness=0.01",
    "hue='H=0.1*PI*t:s=1.03'",
    "eq=contrast=1.1:brightness=0.02:saturation=1.05"
]
chosen_style, chosen_effect = random.choice(styles), random.choice(effects)

# OPTIMIZATION: Removed zoompan filter to keep frames completely in GPU memory pipelines
filter_complex_string = (
    f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
    f"[0:v]scale=918:1632,{chosen_style}[main];"
    f"[bg][main]overlay=(W-w)/2:(H-h)/2,scale=1080:1920,setsar=1[processed_source];"
    f"[2:v]scale=1080:1920,setsar=1[processed_cat];"
    f"[processed_source][processed_cat]concat=n=2:v=1:a=0[merged_video];"
    f"[merged_video]noise=alls=7:allf=t+u[grained];"
    f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v];"
    f"[1:a]atempo={speed_factor}[speed_synced_audio]"
)

ffmpeg_cmd = [
    "ffmpeg", "-y", "-hwaccel", "cuda", 
    "-i", TRIMMED_VIDEO, "-i", NEW_VOICEOVER_MP3, "-i", chosen_cat_file,
    "-filter_complex", filter_complex_string, "-map", "[v]", "-map", "[speed_synced_audio]",
    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", "-c:a", "aac", "-b:a", "128k", "-shortest",
    OUTPUT_VIDEO
]

# Run the execution wrapper cleanly
res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ FFmpeg transformative execution crashed: {res.stderr}")
    raise RuntimeError("FFmpeg Pipeline Failure")
print(f"🚀 GPU Render Complete! Video Saved: {OUTPUT_VIDEO}")


# ==========================================
# 6. UPLOAD TO YOUTUBE SHORTS FEED
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