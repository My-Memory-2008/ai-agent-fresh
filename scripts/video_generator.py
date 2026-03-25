import os
import subprocess
import json
import requests
import time
from gtts import gTTS
from groq import Groq

print("🎬 Starting AI Video Generation...")

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

print("📄 Plan loaded")

# 1. Parse scenes using Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])

scene_prompt = f"""
Extract 5 scenes from this video plan. Return JSON array:
[
  {{"scene": 1, "text": "Title", "prompt": "Detailed cinematic image prompt", "duration": 5}}
]

Video Plan:
{plan}

Make each scene 5 seconds. Be specific with image prompts.
"""

print("🧠 Parsing scenes...")
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": scene_prompt}],
    max_tokens=1000
)

try:
    scenes = json.loads(response.choices[0].message.content)
except:
    scenes = [
        {"scene": 1, "text": "Introduction", "prompt": "Cinematic space scene with stars planets nebula", "duration": 5},
        {"scene": 2, "text": "Main Content", "prompt": "Professional tutorial setup educational", "duration": 5},
        {"scene": 3, "text": "Details", "prompt": "Detailed close-up view technical", "duration": 5},
    ]

print(f"✅ Parsed {len(scenes)} scenes")

# 2. Generate AI images using Pollinations.ai (FREE, NO AUTH!)
print("🎨 Generating AI images...")
os.makedirs("scenes", exist_ok=True)

for i, scene in enumerate(scenes):
    print(f"  Generating scene {i+1}: {scene.get('text')}...")
    
    prompt = scene.get("prompt", "Beautiful cinematic scene")
    duration = scene.get("duration", 5)
    text = scene.get("text", f"Scene {i+1}")
    
    # Use Pollinations.ai - FREE, no authentication needed!
    try:
        # Encode prompt for URL
        encoded_prompt = requests.utils.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true"
        
        print(f"    📥 Downloading from Pollinations...")
        response = requests.get(image_url, timeout=30)
        
        if response.status_code == 200:
            with open(f"scenes/scene_{i+1}.png", "wb") as f:
                f.write(response.content)
            print(f"    ✅ AI image generated successfully!")
        else:
            raise Exception("Download failed")
            
    except Exception as e:
        print(f"    ⚠️ Using fallback: {str(e)}")
        # Fallback: Create colored scene
        colors = ["blue", "purple", "teal", "orange", "red"]
        color = colors[i % len(colors)]
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color}:s=1920x1080:d=1",
            "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{text}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=48:fontcolor=white",
            "-frames:v", "1",
            f"scenes/scene_{i+1}.png"
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
voice_duration = float(result.stdout.strip())

# 4. Create video from images with Ken Burns effect
print("🎥 Creating video with motion effects...")

total_duration = sum(scene.get("duration", 5) for scene in scenes)
scale_factor = voice_duration / total_duration if total_duration > 0 else 1

with open("scenes_list.txt", "w") as f:
    for i, scene in enumerate(scenes):
        duration = scene.get("duration", 5) * scale_factor
        f.write(f"file 'scenes/scene_{i+1}.mp4'\n")
        
        # Create video from image with Ken Burns effect
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", f"scenes/scene_{i+1}.png",
            "-t", str(duration),
            "-vf", "zoompan=z='min(zoom+0.0015,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            f"scenes/scene_{i+1}.mp4"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Concatenate scenes
subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "scenes_list.txt",
    "-c", "copy",
    "temp_concat.mp4"
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Add voiceover
subprocess.run([
    "ffmpeg", "-y",
    "-i", "temp_concat.mp4",
    "-i", "voiceover.mp3",
    "-c:v", "libx264",
    "-preset", "medium",
    "-r", "30",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    "-pix_fmt", "yuv420p",
    "output_video.mp4"
], check=True)

print("✅ Final video created: output_video.mp4")
print("🎬 Video generation complete!")
print(f"📊 Specs: 30fps, 1920x1080, AI images, Ken Burns effects, AAC audio")
