import os
import subprocess

print("🎬 Starting Video Generation...")

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

print("📄 Plan loaded")

# 1. Generate Voiceover using Edge-TTS (Free Microsoft TTS)
print("🎤 Generating voiceover...")
try:
    subprocess.run([
        "edge-tts",
        "--voice", "en-US-Mike",
        "--text", plan,
        "--write-media", "voiceover.mp3"
    ], check=True)
    print("✅ Voiceover created: voiceover.mp3")
except Exception as e:
    print(f"❌ Voiceover failed: {e}")
    # Create a dummy audio file if TTS fails
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=mono",
        "-t", "60",
        "-c:a", "aac",
        "voiceover.mp3"
    ])
    print("⚠️ Created dummy audio (60s silence)")

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

# 3. Create video with black background + voiceover
print("🎥 Assembling video...")
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi",
    "-i", f"color=c=black:s=1920x1080:d={duration}",
    "-i", "voiceover.mp3",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-c:a", "aac",
    "-shortest",
    "output_video.mp4"
], check=True)

print("✅ Video created: output_video.mp4")
print(f"📏 Duration: {duration:.2f}s")
print("🎬 Video generation complete!")
