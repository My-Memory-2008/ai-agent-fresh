# %% [code]
import subprocess
import sys
# Injected tesseract-ocr system packages into your working baseline
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
    "pytesseract", # Core OCR tracking module
    "groq"          # Official Groq API client
]

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + packages)

print("✅ Dependencies installed. Ready for main script.")

#!/usr/bin/env python3
# production_pipeline.py
# Fully Automated YouTube Shorts Engine: Download → Visual Transformation → Upload → Ledger Update
import os, json, re, requests, subprocess, time, random, torch, asyncio
import cv2
import pytesseract
from pytesseract import Output
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

reel_url = pipeline.get("reel_url")
shortcode = pipeline.get("shortcode")
username = pipeline.get("username", "unknown")
incoming_source_script = pipeline.get("script_text", "Watching this precision should be a full time job.")
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
# 3b. IN-KAGGLE LLAMA 3.3 SATISFYING COMMENTARY GENERATOR
# ==========================================
print("🧠 Launching native Llama 3.3 text-analysis engine through official SDK channels...")
groq_key = secrets.get_secret("GROQ_API_KEY")

# Safe default fallback settings
seo_metadata = {
    "title": "Oddly Satisfying Slicing Challenge! 🤯 #shorts",
    "description": "Wait for the ending cat reaction loop! #shorts #satisfying",
    "tags": ["satisfying", "asmr", "shorts"]
}
transformative_commentary_script = "Watching this precision should be a full time job. Stick around for the ending, because it is purely therapeutic."

if groq_key:
    try:
        from groq import Groq
        client = Groq(api_key=groq_key.strip())
        
        seo_prompt = (
            f"You are a viral YouTube Shorts creator specializing in Oddly Satisfying and ASMR commentary. "
            f"A video clip by @{username} is being heavily edited with video filters and finishes with a random funny cat reaction punchline.\n\n"
            f"Context from source video text: \"{incoming_source_script}\".\n\n"
            f"Tasks:\n"
            f"1. SCRIPT_TEXT: Write a fast-paced, highly engaging 14-second human-like commentary (Max 40 words). "
            f"Use a relatable, humorous tone or a satisfying rating scale. Focus on why the video is mesmerizing, "
            f"hype up the precision of the clip, and explicitly tell viewers to stick around for the surprise cat reaction loop at the very end.\n"
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
        
        clean_json_text = chat_completion.choices[0].message.content.strip().replace('```json', '').replace('```', '').strip()
        ai_seo_data = json.loads(clean_json_text)
        
        transformative_commentary_script = ai_seo_data.get('script_text', transformative_commentary_script)
        seo_metadata = {
            "title": ai_seo_data.get('youtube_title', seo_metadata["title"]),
            "description": ai_seo_data.get('youtube_description', seo_metadata["description"]),
            "tags": ai_seo_data.get('youtube_tags', seo_metadata["tags"])
        }
        print(f"🎉 Llama Generation Verified: \"{transformative_commentary_script}\"")
    except Exception as e:
        print(f"⚠️ Groq internal block fallback applied: {e}")

with open(SEO_MANIFEST_PATH, 'w') as f:
    json.dump(seo_metadata, f, indent=2)



# ==========================================
# 4. AI OCR CHECKPOINT: USERNAME WATERMARK REMOVER
# ==========================================
print("👁️ Scanning frame layers for creator username text signatures...")
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
# 4b. NATIVE AUDIO GENERATION & TIMELINE TRIMMING
# ==========================================
def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

orig_duration = get_duration(PROCESSING_INPUT_VIDEO)
trim_target_duration = max(2.0, orig_duration - 4.0) 
print(f"✂️ Trimming target source video timeline boundaries down to: {trim_target_duration:.2f}s")

subprocess.run(["ffmpeg", "-y", "-i", PROCESSING_INPUT_VIDEO, "-t", str(trim_target_duration), "-c:v", "copy", "-c:a", "copy", TRIMMED_VIDEO], check=True, capture_output=True)

print("🎙️ Querying Edge-TTS with clean commentary copy...")
async def generate_edge_voice():
    import edge_tts
    communicate = edge_tts.Communicate(transformative_commentary_script, "en-US-ChristopherNeural")
    await communicate.save(NEW_VOICEOVER_MP3)

if os.path.exists(NEW_VOICEOVER_MP3): os.remove(NEW_VOICEOVER_MP3)
asyncio.run(generate_edge_voice())

while not os.path.exists(NEW_VOICEOVER_MP3) or os.path.getsize(NEW_VOICEOVER_MP3) == 0:
    time.sleep(0.5)
print("✅ Verified clean native voiceover tracking asset saved.")

# ==========================================
# 4c. DATASET CAT REACTION LOADING & SPEED CALCULATOR
# ==========================================
cat_dataset_dir = "/kaggle/input/datasets/muhammadasjad2008/cat-reactions-vault"
if os.path.exists(cat_dataset_dir):
    valid_clips = [os.path.join(root, f) for root, _, files in os.walk(cat_dataset_dir) for f in files if f.endswith('.mp4')]
    chosen_cat_file = random.choice(valid_clips) if valid_clips else PROCESSING_INPUT_VIDEO
else:
    chosen_cat_file = PROCESSING_INPUT_VIDEO
print(f"🐱 Loaded Dataset Reaction Asset: {chosen_cat_file}")

tts_duration = get_duration(NEW_VOICEOVER_MP3)
total_new_duration = trim_target_duration + 4.0 
speed_factor = tts_duration / total_new_duration
if speed_factor < 0.5: speed_factor = 0.5
if speed_factor > 2.0: speed_factor = 2.0
print(f"⏩ Required Voiceover Speed Factor: {speed_factor:.2f}x")

# ==========================================
# 5. GPU-ACCELERATED PROCEDURAL RENDERING
# ==========================================
print("🎬 Rendering multi-layer canvas via NVIDIA NVENC GPU...")
styles = [
    "eq=contrast=1.05:brightness=0.01:saturation=1.02:gamma=0.97",
    "curves=m='0/0 0.25/0.18 0.5/0.5 0.75/0.82 1/1'",
    "eq=contrast=0.95:brightness=0.02:saturation=0.92:gamma=1.04"
]
effects = [
    "zoompan=z='min(zoom+0.003,1.12)':x='iw/2-iw/zoom/2+sin(time*2.5)*6':y='ih/2-ih/zoom/2':d=1",
    "convolution='-1 -1 -1 -1 9 -1 -1 -1 -1',eq=contrast=1.06:brightness=0.01",
    "hue='H=2.5*PI*t:s=1.03'"
]
chosen_style, chosen_effect = random.choice(styles), random.choice(effects)

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
subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
print(f"🚀 GPU Compilation finished successfully: {OUTPUT_VIDEO}")

# ==========================================
# 6. UPLOAD TO YOUTUBE SHORTS FEED
# ==========================================
print("📤 Uploading directly to YouTube Shorts engine feed...")
yt_url = None
upload_success = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    
    creds = Credentials(token=None, refresh_token=YT_REFRESH_TOKEN,
                        token_uri="https://googleapis.com",
                        client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET,
                        scopes=["https://googleapis.com"])
    if creds.expired: creds.refresh(Request())
    
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": seo_metadata["title"],
            "description": seo_metadata["description"] + "\n\n#shorts #asmr #satisfying #viral",
            "tags": seo_metadata["tags"] + ["shorts", "ShortsFeed"],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public", 
            "selfDeclaredMadeForKids": False
        }
    }
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=MediaFileUpload(OUTPUT_VIDEO, chunksize=-1, resumable=True))
    response = request.execute()
    yt_url = f"https://youtube.com{response['id']}"
    upload_success = True
    print(f"🎉 YouTube Shorts Success: {yt_url}")
except Exception as e:
    print(f"⚠️ Upload failed (video saved locally): {e}")

# ==========================================
# 7. UPDATE GITHUB LEDGER
# ==========================================
print("🔄 Updating GitHub ledger tracking lines...")
try:
    from datetime import datetime, timezone
    led_url = f"https://github.com{GITHUB_USER}/{GITHUB_REPO}/contents/reel_queue.json"
    headers_gh = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp_gh = requests.get(led_url, headers=headers_gh)
    current = json.loads(requests.utils.b64decode(resp_gh.json()["content"]).decode())
    
    for entry in current.get('processed', []):
        if entry['url'] == reel_url and entry.get('status') == 'in_progress':
            entry['status'] = 'success' if upload_success else 'failed'
            if yt_url: entry['youtube_url'] = yt_url
            entry['completed_at'] = datetime.now(timezone.utc).isoformat()
            break
            
    new_content = requests.utils.b64encode(json.dumps(current).encode()).decode()
    requests.put(led_url, headers=headers_gh, json={"message": "Auto: Updated reel status", "content": new_content, "sha": resp_gh.json()["sha"]})
    print("✅ Ledger successfully updated.")
except Exception as e:
    print(f"⚠️ Ledger warning: {e}")

print("\n🏆 IN-KAGGLE PRODUCTION PIPELINE COMPLETE!")
