import os
import subprocess
import time

print("🎬 Starting Video Generation...")

# Read the plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

# 1. Generate Voiceover
print("🎤 Generating voiceover...")
subprocess.run([
    "edge-tts",
    "--voice", "en-US-Mike",
    "--text", plan,
    "--write-media", "voiceover.mp3"
])
print("✅ Voiceover created: voiceover.mp3")

# 2. Create a simple video with black background + voice
# (We'll add AI images in the next iteration)
print("🎥 Creating video...")
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi",
    "-i", "color=c=black:s=1920x1080:d=60",
    "-i", "voiceover.mp3",
    "-c:v", "libx264",
    "-c:a", "aac",
    "-shortest",
    "output_video.mp4"
])
print("✅ Video created: output_video.mp4")

print("🎬 Video generation complete!")
