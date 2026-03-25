import os
from groq import Groq

# Setup
client = Groq(api_key=os.environ["GROQ_API_KEY"])
prompt = f"{os.environ['ISSUE_TITLE']}: {os.environ['ISSUE_BODY']}"

# The 3 Models (All Currently Working on Groq)
models = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama-3.2-11b-vision-preview"
]

results = []
print(f"🚀 Starting Council for: {prompt}")

for model in models:
    try:
        print(f"🧠 Asking {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": f"Create a detailed video plan for: {prompt}"}],
            max_tokens=400
        )
        text = response.choices[0].message.content
        results.append(f"✅ **{model}**:\n{text}")
        print(f"✅ Got response from {model}")
    except Exception as e:
        print(f"❌ {model} failed: {str(e)}")
        results.append(f"❌ **{model}**: Failed")

# Synthesis
final_output = "## 🎬 AI Council Results\n\n" + "\n\n---\n\n".join(results)

# Save
with open("final_plan.txt", "w") as f:
    f.write(final_output)
print("✅ Done")
