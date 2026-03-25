import os
import subprocess

print("🎬 Starting Video Generation...")

# Read the master plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

print("📄 Plan loaded")

# 1. Generate Voiceover using Edge-TTS (Fixed voice name)
print("🎤 Generating voiceover...")
try:
    subprocess.run([
        "edge-tts",
        "--voice", "en-US-AriaNeural",  # ✅ Fixed: Valid voice
        "--text", plan,
        "--write-media", "voiceover.mp3"
    ], check=True)
    print("✅ Voiceover created: voiceover.mp3")
except Exception as e:
    print(f"❌ Voiceover failed: {e}")
    print("⚠️ Creating silent audio fallback...")
    # Create 60 seconds of silence
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "60",
        "voiceover.mp3"
    ])
    print("⚠️ Created 60s silent audio")

# 2. Get audio duration
print("⏱️ Calculating duration...")
try:
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        "voiceover.mp3"
    ], capture_output=True, text=True)
    
    duration = float(result.stdout.strip()) if result.stdout.strip() else 60
except:
    duration = 60
    
print(f"📊 Audio duration: {duration:.2f} seconds")

# 3. Create video with black background + voiceover
print("🎥 Assembling video...")
try:
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1920x1080:d={duration}",
        "-i", "voiceover.mp3",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "output_video.mp4"
    ], check=True)
    print("✅ Video created: output_video.mp4")
except Exception as e:
    print(f"❌ Video assembly failed: {e}")
    # Create a dummy video file
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s=1920x1080:d=60",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "output_video.mp4"
    ])
    print("⚠️ Created dummy 60s black video")

print("🎬 Video generation complete!")
