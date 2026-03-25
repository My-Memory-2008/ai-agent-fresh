import os
import subprocess
from groq import Groq

# Get the plan
with open("final_plan.txt", "r") as f:
    plan = f.read()

print("🎬 Generating Voiceover...")

# 1. Generate Voiceover (Free Edge-TTS)
subprocess.run([
    "edge-tts",
    "--voice", "en-US-Mike",
    "--text", plan,
    "--write-media", "voiceover.mp3"
])

print("✅ Voiceover generated")

# 2. Generate Script for Images
client = Groq(api_key=os.environ["GROQ_API_KEY"])
image_prompts = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": f"Create 5 detailed image generation prompts for this video plan: {plan}"}],
    max_tokens=300
)

prompts = image_prompts.choices[0].message.content.split("\n")
print(f"🎨 Generated {len(prompts)} image prompts")

# 3. Save prompts for next step
with open("image_prompts.txt", "w") as f:
    f.write(prompts[0] if prompts else "Tokyo travel scenery")

print("✅ Video assets prepared")
