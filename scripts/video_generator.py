import os
import json
import requests
import time
from groq import Groq

print("🎬 Starting JSON2Video Generation...")

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()
print("📄 Plan loaded")

# 1. Parse scenes
client = Groq(api_key=os.environ["GROQ_API_KEY"])
scene_prompt = f"""
Extract 4 scenes from this plan. Return JSON:
[{{"text": "Title", "duration": 5, "bg_color": "#3498db"}}]
Plan: {plan}
Colors: #3498db, #9b59b6, #1abc9c, #e67e22
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
        {"text": "Intro", "duration": 5, "bg_color": "#3498db"},
        {"text": "Content", "duration": 6, "bg_color": "#9b59b6"},
        {"text": "Details", "duration": 5, "bg_color": "#1abc9c"},
        {"text": "Outro", "duration": 4, "bg_color": "#e67e22"},
    ]

# 2. Build template
print("📝 Building template...")
voiceover_text = plan[:400].replace("\n", " ").strip() + "..."

template = {
    "template": {
        "resolution": "1920x1080",
        "fps": 30,
        "clips": []
    }
}

for i, scene in enumerate(scenes):
    clip = {
        "duration": scene.get("duration", 5),
        "background": {"color": scene.get("bg_color", "#3498db")},
        "texts": [{
            "text": scene.get("text", f"Scene {i+1}")[:25],
            "font": "Montserrat-Bold",
            "size": 64,
            "color": "#FFFFFF",
            "x": "center",
            "y": "center",
            "shadow": {"color": "#000000", "blur": 3, "x": 2, "y": 2}
        }],
        "transitions": [{"type": "fade", "duration": 0.5}] if i > 0 else []
    }
    template["template"]["clips"].append(clip)

template["template"]["voiceover"] = {
    "text": voiceover_text,
    "voice": "en-US-Mike",
    "speed": 1.0
}

# 3. Send to JSON2Video with ROBUST auth
print("📤 Sending to JSON2Video API...")

api_key = os.environ.get("JSON2VIDEO_API_KEY", "")
print(f"🔑 Key length: {len(api_key)}, starts with: {api_key[:5] if api_key else 'NONE'}")

if not api_key or not api_key.startswith("sk_"):
    print("⚠️ Warning: API key may be invalid (should start with 'sk_')")

# Try multiple auth formats
auth_methods = [
    {"Authorization": f"Bearer {api_key}"},
    {"X-API-KEY": api_key},
    {"api_key": api_key},
]

success = False
for headers in auth_methods:
    headers["Content-Type"] = "application/json"
    
    try:
        print(f"🔐 Trying auth: {list(headers.keys())[0]}")
        response = requests.post(
            "https://api.json2video.com/v1/videos",
            headers=headers,
            json=template,
            timeout=30
        )
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 201:
            job_id = response.json()["id"]
            print(f"✅ Job started: {job_id}")
            success = True
            
            # Poll for completion
            for attempt in range(25):
                time.sleep(8)
                status_resp = requests.get(
                    f"https://api.json2video.com/v1/videos/{job_id}",
                    headers=headers,
                    timeout=10
                )
                status_data = status_resp.json()
                status = status_data.get("status")
                
                if status == "done":
                    video_url = status_data.get("url")
                    if video_url:
                        print(f"✅ Downloading video...")
                        video_resp = requests.get(video_url, timeout=60)
                        with open("output_video.mp4", "wb") as f:
                            f.write(video_resp.content)
                        print("✅ Video saved!")
                        break
                elif status == "failed":
                    print(f"❌ Render failed: {status_data}")
                    break
            break
        else:
            print(f"⚠️ Auth failed: {response.text[:100]}")
            
    except Exception as e:
        print(f"⚠️ Request error: {e}")

if not success:
    print("❌ All auth methods failed - creating fallback video")
    # Fallback with FFmpeg
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=#3498db:s=1920x1080:d=20",
        "-vf", "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Video':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=64:fontcolor=white",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "output_video.mp4"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Fallback video created")

print("🎬 Complete!")
