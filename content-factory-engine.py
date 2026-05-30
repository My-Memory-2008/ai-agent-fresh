# %% [code]
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
    "edge-tts",
    "groq"
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
# 4. STEP 1: EXECUTE ALL VIDEO EDITING TRANSFORMATIONS FIRST
# ==========================================
print("🚀 Step 1: Initiating full visual editing transformation canvas...")

# Define internal rendering layer workspace file paths explicitly
EDITED_SOURCE_ONLY = "/kaggle/working/edited_source_only.mp4"
STANDARDIZED_CAT_ONLY = "/kaggle/working/standardized_cat_only.mp4"
OUTPUT_VIDEO = "/kaggle/working/final_youtube_short.mp4"

# Raw audio tracking layers to force absolute sound mapping parameters
AUDIO1_WAV = "/kaggle/working/track1.wav"
AUDIO2_WAV = "/kaggle/working/track2.wav"
MERGED_AUDIO_WAV = "/kaggle/working/merged_audio.wav"

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

# --- AI OCR CHECKPOINT: USERNAME WATERMARK REMOVER ---
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
    CLEAN_INPUT_STAGE1 = "/kaggle/working/ocr_cleaned_source.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", output_path, "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}", "-c:a", "copy", CLEAN_INPUT_STAGE1], check=True, capture_output=True)
else:
    print("✨ Clean Layout Check! Bypassing OCR erasure step.")
    CLEAN_INPUT_STAGE1 = output_path

# --- APPLY 9:16 PORTRAIT VISUAL EDITING FILTER STACK ---
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

filter_complex_editing = (
    f"[0:v]scale=1080:1920,boxblur=25:5,{chosen_effect}[bg];"
    f"[0:v]scale=918:1632,{chosen_style}[main_scaled];"
    f"[bg][main_scaled]overlay=(W-w)/2:(H-h)/2,setsar=1[processed_source];"
    f"[processed_source]noise=alls=7:allf=t+u[grained];"
    f"[grained]drawtext=text='@AWRAM':x=(w-tw)/2:y=80:fontsize=40:fontcolor=white@0.55:box=1:boxcolor=black@0.25[v]"
)

# Render Step 1: Fully process video transformations into constant 30fps container lanes
ffmpeg_editing = [
    "ffmpeg", "-y", "-hwaccel", "cuda", 
    "-i", CLEAN_INPUT_STAGE1,          
    "-filter_complex", filter_complex_editing, 
    "-map", "[v]",      
    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", "-r", "30", "-pix_fmt", "yuv420p",
    EDITED_SOURCE_ONLY
]

res1 = subprocess.run(ffmpeg_editing, capture_output=True, text=True)
if res1.returncode != 0:
    print(f"❌ Editing phase crashed: {res1.stderr}")
    raise RuntimeError("FFmpeg Editing Canvas Failure")
print("✅ Step 1 Complete: Visual layers processed successfully.")




# ==========================================
# 4b. MULTIMODAL VISION AI VIRAL SEO GENERATOR (NO REPEATS)
# ==========================================
print("🧠 Activating Local Multimodal Vision AI Engine on GPU...")
import torch
import cv2
import json
import os
from PIL import Image

SEO_MANIFEST_PATH = "/kaggle/working/seo_metadata.json"

# Safety default fallback metadata structure
seo_metadata = {
    "title": "Most Oddly Satisfying ASMR Challenge! 🤯 #shorts",
    "description": "Wait till the end for the funny cat reaction loop! Original concept inspired by creator. #shorts #asmr",
    "tags": ["satisfying", "asmr", "shorts", "relaxing"]
}

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_id = "vikhyatk/moondream2"
    revision = "2024-08-26" # Stable production checkpoint for T4 card memory bounds
    
    print("📥 Loading vision-language weights into NVIDIA T4 VRAM maps...")
    
    # 🔥 FIXED: Added trust_remote_code=True here to eliminate the interactive [y/N] script hang prompt
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, trust_remote_code=True)
    
    # 🔥 FIXED: Initialized model using native AutoModelForCausalLM config layers to avoid the pad_token_id exception
    model = AutoModelForCausalLM.from_pretrained(
        model_id, 
        revision=revision, 
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        attn_implementation="eager"
    ).to("cuda")
    model.eval()
    print("🎯 Vision engine is live and listening.")

    # 1. Capture a mid-timeline frame directly from your edited source video file
    print(f"👁️ Extracting frame data matrix for structural visual analysis from: {EDITED_SOURCE_ONLY}")
    cap = cv2.VideoCapture(EDITED_SOURCE_ONLY)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_count * 0.45)) # Grab frame right in the middle of action
    ret, frame = cap.read()
    cap.release()

    if ret:
        # Convert raw CV2 BGR layout to Standard PIL RGB for the neural vision layers
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        
        # 2. Fire structural analysis query to describe the unique visual elements of this specific clip
        print("📡 Inspecting video frame visuals...")
        
        # Run vision encoder sequence maps natively
        with torch.no_grad():
            image_embeds = model.encode_image(pil_image)
            visual_analysis = model.answer_question(
                image_embeds, 
                "Describe exactly what action, objects, colors, or materials are visible in this scene in 1 sentence. Be highly specific.", 
                tokenizer
            )
        print(f"📸 Vision Scanner result: \"{visual_analysis}\"")

        # 3. Use the visual description to construct completely custom SEO metrics dynamically
        print("✍️ Extrapolating trending metadata structures...")
        
        clean_desc = visual_analysis.replace('"', '').replace('.', '').strip()
        
        generated_title = f"This {clean_desc} Is So Addictive! 🤯 #shorts"
        if len(generated_title) > 65:
            generated_title = f"Oddly Satisfying {clean_desc[:30]}! 🔥 #shorts"
            
        generated_desc = (
            f"Can't stop watching this satisfying video showing {clean_desc.lower()}. "
            f"The precision and flow in this loop is completely mesmerizing and therapeutic. "
            f"Stick around for the surprise funny cat reaction loop at the end! Inspired by @{username}. Subscribe for more!"
        )
        
        # Dynamically build tag vectors matching the video content strings
        base_tags = ["satisfying", "asmr", "shorts", "viral"]
        visual_keywords = [word.lower().strip(",.") for word in clean_desc.split() if len(word) > 4][:2]
        generated_tags = base_tags + visual_keywords
        
        seo_metadata = {
            "title": generated_title,
            "description": generated_desc,
            "tags": generated_tags[:6]
        }
        print(f"🎉 SUCCESS! Fresh Visual SEO Generated -> Title: \"{seo_metadata['title']}\"")
    else:
        raise RuntimeError("Frame capture extraction failed.")

except Exception as vision_error:
    print(f"⚠️ Local vision block failed, using system fallback arrays: {vision_error}")

# Clean up GPU tracking tensors from VRAM to prevent downstream rendering halts
if 'model' in locals(): del model
if 'tokenizer' in locals(): del tokenizer
torch.cuda.empty_cache()

# Save metadata manifest file to drive partition for Section 6 upload mapping
with open(SEO_MANIFEST_PATH, 'w') as f:
    json.dump(seo_metadata, f, indent=2)



# ==========================================
# 5. STEP 2: SELECT AND CONVERT THE CAT VIDEO STRUCTURE
# ==========================================
print("🎬 Step 2: Selecting random reaction clip and matching visual parameters exactly...")

cat_dataset_dir = "/kaggle/input/datasets/muhammadasjad2008/cat-reactions-vault"
if os.path.exists(cat_dataset_dir):
    valid_clips = [os.path.join(root, f) for root, _, files in os.walk(cat_dataset_dir) for f in files if f.endswith('.mp4')]
    chosen_cat_file = random.choice(valid_clips) if valid_clips else output_path
else:
    chosen_cat_file = output_path
print(f"🐱 Selected Cat Reaction Asset: {chosen_cat_file}")

# Normalize the cat video track alone down to constant 30fps frames 
ffmpeg_standardize_cat = [
    "ffmpeg", "-y", "-hwaccel", "cuda",
    "-i", chosen_cat_file,
    "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
    "-an", # Drop audio stream temporarily from the video container to bypass format locks
    "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", "-r", "30", "-pix_fmt", "yuv420p",
    STANDARDIZED_CAT_ONLY
]
subprocess.run(ffmpeg_standardize_cat, check=True, capture_output=True)
print("✅ Step 2 Complete: Visual video frame timelines safely standardized.")

# ==========================================
# 5b. STEP 3: EXTRACT RAW UNCOMPRESSED AUDIO TRACKS
# ==========================================
print("🎙️ Step 3: Extracting raw uncompressed PCM audio matrices to prevent muting faults...")

def get_duration(file_path):
    cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {file_path}"
    return float(subprocess.check_output(cmd, shell=True).decode().strip())

duration1 = get_duration(EDITED_SOURCE_ONLY)
duration2 = get_duration(STANDARDIZED_CAT_ONLY)

# Convert track 1 audio into raw uncompressed WAV layout
subprocess.run(["ffmpeg", "-y", "-i", CLEAN_INPUT_STAGE1, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", "-t", str(duration1), AUDIO1_WAV], check=True, capture_output=True)

# Convert track 2 audio (cat video) into raw uncompressed WAV layout. If it lacks sound, it pads with silent track layers natively.
try:
    subprocess.run(["ffmpeg", "-y", "-i", chosen_cat_file, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", "-t", str(duration2), AUDIO2_WAV], check=True, capture_output=True)
except Exception:
    print("-> Selected cat clip is audio-less. Generating explicit silent track matrix loop...")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-acodec", "pcm_s16le", "-t", str(duration2), AUDIO2_WAV], check=True, capture_output=True)

# Concat the raw WAV audio arrays back-to-back inside system space
print("🤝 Fusing audio arrays cleanly inside system buffers...")
subprocess.run(["ffmpeg", "-y", "-i", AUDIO1_WAV, "-i", AUDIO2_WAV, "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]", "-map", "[a]", "-acodec", "pcm_s16le", MERGED_AUDIO_WAV], check=True, capture_output=True)
print("✅ Step 3 Complete: Raw audio tracks securely linked without data drops.")

# ==========================================
# 5c. STEP 4: STITCH TIMELINES VIA MULTIPLEX STREAM CONTAINER MAPPING
# ==========================================
print("🎬 Step 4: Stitching completed video containers and injecting the unmuted sound track track loop...")

# Join video blocks cleanly via demuxer tracking list
concat_list_path = "/kaggle/working/concat_list.txt"
with open(concat_list_path, "w") as f:
    f.write(f"file '{EDITED_SOURCE_ONLY}'\n")
    f.write(f"file '{STANDARDIZED_CAT_ONLY}'\n")

TEMP_SILENT_MP4 = "/kaggle/working/temp_silent_output.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", TEMP_SILENT_MP4], check=True, capture_output=True)

# Multiplex the combined uncompressed sound track loop and the video together instantly (Takes 0.4 seconds)
ffmpeg_final_mux = [
    "ffmpeg", "-y",
    "-i", TEMP_SILENT_MP4,
    "-i", MERGED_AUDIO_WAV,
    "-map", "0:v", "-map", "1:a", # Map the full video timeline and the unmuted linked audio track back-to-back
    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
    OUTPUT_VIDEO
]
subprocess.run(ffmpeg_final_mux, check=True, capture_output=True)
print(f"🎉 SUCCESS! Video completely compiled at its exact length with unmuted cat audio: {OUTPUT_VIDEO}")


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
        "snippet": {
            "title": seo_metadata["title"],
            "description": seo_metadata["description"] + "\n\n#shorts #asmr #satisfying #viral",
            "tags": seo_metadata["tags"] + ["shorts", "ShortsFeed"],
            "categoryId": "22"
        },
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
