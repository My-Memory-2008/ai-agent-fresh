import os
import json
import requests
import subprocess
from gtts import gTTS
from groq import Groq

print("🎬 Starting Pexels Stock Photo Video Generation...")

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()
print("📄 Plan loaded")

# 1. Parse scenes using Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])

scene_prompt = f"""
Extract 4 scenes from this video plan. Return JSON array:
[{{"text": "Short title", "keyword": "search term", "duration": 5}}]

Video Plan: {plan}

Keywords should be single words or simple phrases like:
nature, technology, food, travel, business, ocean, mountain, city, etc.
Keep text under 25 characters.
"""

print("🧠 Parsing scenes...")
try:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": scene_prompt}],
        max_tokens=500
    )
    scenes = json.loads(response.choices[0].message.content)
    print(f"✅ Parsed {len(scenes)} scenes")
except Exception as e:
    print(f"⚠️ Using fallback: {e}")
    scenes = [
        {"text": "Intro", "keyword": "nature landscape", "duration": 5},
        {"text": "Content", "keyword": "technology computer", "duration": 6},
        {"text": "Details", "keyword": "business office", "duration": 5},
        {"text": "Outro", "keyword": "success celebration", "duration": 4},
    ]

# 2. Download images from Pexels (FREE API)
print("🎨 Downloading stock photos from Pexels...")
os.makedirs("scenes", exist_ok=True)

pexels_api_key = os.environ.get("PEXELS_API_KEY", "")
headers = {"Authorization": pexels_api_key} if pexels_api_key else {}

for i, scene in enumerate(scenes):
    text = scene.get("text", f"Scene {i+1}")[:25]
    keyword = scene.get("keyword", "nature")
    duration = scene.get("duration", 5)
    
    print(f"  Scene {i+1}: {text} (searching: {keyword})")
    
    try:
        # Search Pexels API
        search_url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=1&orientation=landscape"
        response = requests.get(search_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("photos"):
                photo_url = data["photos"][0]["src"]["landscape"]
                
                # Download the image
                img_response = requests.get(photo_url, timeout=15)
                if img_response.status_code == 200:
                    with open(f"scenes/scene_{i+1}.jpg", "wb") as f:
                        f.write(img_response.content)
                    print(f"    ✅ Downloaded: {data['photos'][0]['photographer']}")
                else:
                    raise Exception("Download failed")
            else:
                raise Exception("No photos found")
        else:
            raise Exception(f"API error: {response.status_code}")
            
    except Exception as e:
        print(f"    ⚠️ Fallback: {str(e)[:50]}")
        # Create colored fallback
        colors = ["#3498db", "#9b59b6", "#1abc9c", "#e67e22"]
        color = colors[i % len(colors)]
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color}:s=1920x1080:d=1",
            "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{text}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=64:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2",
            "-frames:v", "1",
            f"scenes/scene_{i+1}.jpg"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 3. Generate voiceover
print("🎤 Generating voiceover...")
tts = gTTS(text=plan, lang='en', slow=False)
tts.save("voiceover.mp3")

# Get duration
result = subprocess.run([
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    "voiceover.mp3"
], capture_output=True, text=True)
voice_duration = float(result.stdout.strip()) if result.stdout.strip() else 60

# 4. Create video with Ken Burns effect
print("🎥 Creating video with motion...")

total_duration = sum(scene.get("duration", 5) for scene in scenes)
scale_factor = voice_duration / total_duration if total_duration > 0 else 1

with open("scenes_list.txt", "w") as f:
    for i, scene in enumerate(scenes):
        duration = scene.get("duration", 5) * scale_factor
        f.write(f"file 'scenes/scene_{i+1}.mp4'\n")
        
        # Ken Burns pan/zoom effect
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", f"scenes/scene_{i+1}.jpg",
            "-t", str(duration),
            "-vf", "zoompan=z='min(zoom+0.0015,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080",
            "-c:v", "libx264", "-preset", "ultrafast",
            f"scenes/scene_{i+1}.mp4"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Concatenate scenes
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "scenes_list.txt", "-c", "copy", "temp_concat.mp4"
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Add voiceover
subprocess.run([
    "ffmpeg", "-y",
    "-i", "temp_concat.mp4", "-i", "voiceover.mp3",
    "-c:v", "libx264", "-preset", "medium", "-r", "30",
    "-c:a", "aac", "-b:a", "128k", "-shortest",
    "-pix_fmt", "yuv420p", "output_video.mp4"
], check=True)

print("✅ Video created: output_video.mp4")
print("🎬 Complete!")
