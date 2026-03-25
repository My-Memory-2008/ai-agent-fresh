import os
from groq import Groq

# Setup
client = Groq(api_key=os.environ["GROQ_API_KEY"])
prompt = f"{os.environ['ISSUE_TITLE']}: {os.environ['ISSUE_BODY']}"

# Reliable Models (Text-only)
models = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it"  # Often comes back online
]

results = []
print(f"🚀 Starting Council for: {prompt}")

# 1. Gather Responses
for model in models:
    try:
        print(f"🧠 Asking {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Create a video plan for: {prompt}"}],
            max_tokens=400
        )
        text = response.choices[0].message.content
        results.append(f"{model}: {text}")
        print(f"✅ Got response from {model}")
    except Exception as e:
        print(f"❌ {model} failed: {str(e)}")

# 2. The Judge (Synthesis)
print("⚖️ Judge synthesizing answers...")
try:
    judge_prompt = f"""
You are the Chief Editor. Review these AI plans:
{results}

Task: Combine the best elements into ONE master video plan.
Output Format:
## 🎬 Master Video Plan
**Title:** [Catchy Title]
**Hook:** [0-5s]
**Intro:** [5-15s]
**Content:** [15-45s]
**CTA:** [45-60s]
**Tags:** [5 tags]
"""
    synthesis = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # Use strongest model as Judge
        messages=[{"role": "user", "content": judge_prompt}],
        max_tokens=600
    )
    final_output = synthesis.choices[0].message.content
except Exception as e:
    final_output = "## ❌ Synthesis Failed\n\n" + "\n\n".join(results)

# 3. Save
with open("final_plan.txt", "w") as f:
    f.write(final_output)
print("✅ Done")

# 4. Trigger Video Generation
print("🎬 Starting video generation...")
subprocess.run(["python", "scripts/video_generator.py"])
