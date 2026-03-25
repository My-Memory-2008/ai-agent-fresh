import os
import subprocess
import json
import urllib.request
import ssl
from gtts import gTTS
from groq import Groq

print("🎬 Starting AI Video Generation...")

# Disable SSL verification for GitHub Actions
ssl._create_default_https_context = ssl._create_unverified_context

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

print("📄 Plan loaded")

# 1. Parse scenes using Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])

scene_prompt = f"""
Extract 3 scenes from this video plan. Return JSON array:
[
  {{"scene": 1, "text": "Title", "prompt": "Short simple image prompt", "duration": 5}}
]

Video Plan:
{plan}

Keep prompts short and simple (max 50 characters).
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
    print(f"⚠️ Using fallback scenes: {e}")
    scenes = [
        {"scene": 1, "text": "Introduction", "prompt": "nature mountains landscape", "duration": 5},
        {"scene": 2, "text": "Main Content", "prompt": "educational tutorial learning", "duration": 5},
        {"scene": 3, "text": "Details", "prompt": "close up details technical", "duration": 5},
    ]

# 2. Generate AI images using Pollinations.ai
print("🎨 Generating AI images...")
os.makedirs("scenes", exist_ok=True)

for i, scene in enumerate(scenes):
    print(f"  Generating scene {i+1}...")
    
    prompt = scene.get("prompt", "beautiful landscape")
    # Clean prompt - remove special chars
    prompt = ''.join(c if c.isalnum() or c.isspace() else '' for c in prompt)
    prompt = prompt.replace(" ", "_")[:50]  # Max 50 chars
    
    duration = scene.get("duration", 5)
    text = scene.get("text", f"Scene {i+1}")
    
    # Simpler URL without encoding
    image_url = f"https://image.pollinations.ai/prompt/{prompt}?width=1920&height=1080&nologo=true&seed={i}"
    
    print(f"    URL: {image_url[:80]}...")
    
    try:
        # Use urllib instead of requests (more reliable in GitHub Actions)
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=60)
        
        if response.getcode() == 200:
            with open(f"scenes/scene_{i+1}.png", "wb") as f:
                f.write(response.read())
            print(f"    ✅ AI image downloaded!")
            
            # Verify file size
            file_size = os.path.getsize(f"scenes/scene_{i+1}.png")
            print(f"    📏 File size: {file_size} bytes")
            
            if file_size < 1000:  # Too small = failed image
                raise Exception("Image too small")
        else:
            raise Exception(f"HTTP {response.getcode()}")
            
    except Exception as e:
        print(f"    ⚠️ Fallback: {str(e)[:50]}")
        # Create colored fallback
        colors = ["blue", "purple", "teal"]
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
voice_duration = float(result.stdout.strip()) if result.stdout.strip() else 60

# 4. Create video
print("🎥 Creating video...")

total_duration = sum(scene.get("duration", 5) for scene in scenes)
scale_factor = voice_duration / total_duration if total_duration > 0 else 1

with open("scenes_list.txt", "w") as f:
    for i, scene in enumerate(scenes):
        duration = scene.get("duration", 5) * scale_factor
        f.write(f"file 'scenes/scene_{i+1}.mp4'\n")
        
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", f"scenes/scene_{i+1}.png",
            "-t", str(duration),
            "-vf", "zoompan=z='min(zoom+0.0015,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080",
            "-c:v", "libx264", "-preset", "ultrafast",
            f"scenes/scene_{i+1}.mp4"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "scenes_list.txt", "-c", "copy", "temp_concat.mp4"
], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

subprocess.run([
    "ffmpeg", "-y",
    "-i", "temp_concat.mp4", "-i", "voiceover.mp3",
    "-c:v", "libx264", "-preset", "medium", "-r", "30",
    "-c:a", "aac", "-b:a", "128k", "-shortest",
    "-pix_fmt", "yuv420p", "output_video.mp4"
], check=True)

print("✅ Video created: output_video.mp4")
print("🎬 Complete!")
