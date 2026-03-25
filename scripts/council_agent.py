import os
from huggingface_hub import InferenceClient

# Setup
token = os.environ["HF_TOKEN"]
client = InferenceClient(token=token)
prompt = f"{os.environ['ISSUE_TITLE']}: {os.environ['ISSUE_BODY']}"

# The 3 Models (Stable Free Tier)
models = [
    "microsoft/Phi-3-mini-4k-instruct",
    "mistralai/Mistral-7B-Instruct-v0.2",
    "google/gemma-2b-it"
]

results = []
print(f"🚀 Starting Council for: {prompt}")

for model in models:
    try:
        print(f"🧠 Asking {model}...")
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(model=model, messages=messages, max_tokens=200)
        text = response.choices[0].message.content
        results.append(f"✅ {model.split('/')[-1]}: {text[:100]}...")
    except Exception as e:
        print(f"❌ {model} failed: {str(e)}")
        results.append(f"❌ {model.split('/')[-1]}: Failed")

# Synthesis
final_output = "## 🎬 Council Results\n\n" + "\n\n".join(results)

# Save
with open("final_plan.txt", "w") as f:
    f.write(final_output)
print("✅ Done")
