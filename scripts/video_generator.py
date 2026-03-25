import os
import subprocess
from gtts import gTTS

print("🎬 Starting Video Generation...")

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

print("📄 Plan loaded")

# 1. Generate Voiceover using Google TTS (Free, no blocking)
print("🎤 Generating voiceover with Google TTS...")
try:
    tts = gTTS(text=plan, lang='en', slow=False)
    tts.save("voiceover.mp3")
    print("✅ Voiceover created: voiceover.mp3")
except Exception as e:
    print(f"❌ gTTS failed: {e}")
    # Create silent fallback
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "60",
        "voiceover.mp3"
    ])

# 2. Get audio duration
print("⏱️ Calculating duration...")
result = subprocess.run([
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    "voiceover.mp3"
], capture_output=True, text=True)

duration = float(result.stdout.strip()) if result.stdout.strip() else 60
print(f"📊 Audio duration: {duration:.2f} seconds")

# 3. Create text overlay file
print("📝 Creating text overlay...")
title = "AI Generated Video"
with open("title.txt", "w") as f:
    f.write(title)

# 4. Create video with text overlay + voiceover
print("🎥 Assembling video with text...")
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi",
    "-i", f"color=c=blue:s=1920x1080:d={duration}",
    "-i", "voiceover.mp3",
    "-vf", f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{title}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=48:fontcolor=white",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    "output_video.mp4"
], check=True)

print("✅ Video created: output_video.mp4")
print("🎬 Video generation complete!")
