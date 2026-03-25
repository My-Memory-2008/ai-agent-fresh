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

# 1. Parse scenes using Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])

scene_prompt = f"""
Extract 4-6 scenes from this video plan. Return JSON array:
[
  {{"text": "Short scene title", "duration": 5, "bg_color": "#3498db"}}
]

Video Plan:
{plan}

Use these colors: #3498db (blue), #9b59b6 (purple), #1abc9c (teal), #e67e22 (orange), #e74c3c (red)
Keep text under 30 characters. Duration: 4-7 seconds each.
"""

print("🧠 Parsing scenes...")
try:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": scene_prompt}],
        max_tokens=600
    )
    scenes = json.loads(response.choices[0].message.content)
    print(f"✅ Parsed {len(scenes)} scenes")
except Exception as e:
    print(f"⚠️ Using fallback: {e}")
    scenes = [
        {"text": "Introduction", "duration": 5, "bg_color": "#3498db"},
        {"text": "Main Content", "duration": 6, "bg_color": "#9b59b6"},
        {"text": "Key Points", "duration": 5, "bg_color": "#1abc9c"},
        {"text": "Conclusion", "duration": 4, "bg_color": "#e67e22"},
    ]

# 2. Build JSON2Video template
print("📝 Building video template...")

# Convert plan to short voiceover text (first 500 chars)
voiceover_text = plan[:500].replace("\n", " ").strip() + "..."

template = {
    "template": {
        "resolution": "1920x1080",
        "fps": 30,
        "clips": []
    }
}

# Add scene clips
for i, scene in enumerate(scenes):
    clip = {
        "duration": scene.get("duration", 5),
        "background": {"color": scene.get("bg_color", "#3498db")},
        "texts": [
            {
                "text": scene.get("text", f"Scene {i+1}"),
                "font": "Montserrat-Bold",
                "size": 72,
                "color": "#FFFFFF",
                "x": "center",
                "y": "center",
                "shadow": {"color": "#000000", "blur": 4, "x": 2, "y": 2}
            }
        ],
        "transitions": [
            {"type": "fade", "duration": 0.5}
        ] if i > 0 else []
    }
    template["template"]["clips"].append(clip)

# Add voiceover (text-to-speech via JSON2Video)
template["template"]["voiceover"] = {
    "text": voiceover_text,
    "voice": "en-US-Mike",
    "speed": 1.0
}

print(f"✅ Template built with {len(scenes)} scenes")

# 3. Send to JSON2Video API
print("📤 Sending to JSON2Video API...")
# 3. Send to JSON2Video API
print("📤 Sending to JSON2Video API...")

api_key = os.environ["JSON2VIDEO_API_KEY"]

# JSON2Video uses simple API key header (not Bearer)
headers = {
    "Content-Type": "application/json",
    "X-API-KEY": api_key  # ✅ Correct header format
}

try:
    # Start rendering job
    response = requests.post(
        "https://api.json2video.com/v1/videos",
        headers=headers,
        json=template,
        timeout=30
    )
    
    print(f"📡 Response status: {response.status_code}")
    print(f"📡 Response body: {response.text[:200]}")
    
    if response.status_code == 201:
        job_id = response.json()["id"]
        print(f"✅ Job started: {job_id}")
        
        # Poll for completion
        print("⏳ Waiting for render (up to 3 minutes)...")
        for attempt in range(30):
            time.sleep(6)
            status_resp = requests.get(
                f"https://api.json2video.com/v1/videos/{job_id}",
                headers=headers,
                timeout=10
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            
            print(f"  Attempt {attempt+1}: Status = {status}")
            
            if status == "done":
                video_url = status_data["url"]
                print(f"✅ Video ready: {video_url}")
                
                # Download the video
                print("⬇️ Downloading video...")
                video_resp = requests.get(video_url, timeout=60)
                with open("output_video.mp4", "wb") as f:
                    f.write(video_resp.content)
                print("✅ Video saved: output_video.mp4")
                break
            elif status == "failed":
                print(f"❌ Render failed: {status_data.get('error')}")
                break
        else:
            print("⚠️ Timeout - video still rendering")
    else:
        print(f"❌ API error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Request failed: {e}")
    import traceback
    traceback.print_exc()

print("🎬 Complete!")
