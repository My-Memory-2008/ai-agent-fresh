import os
import requests
import time
from datetime import datetime

print("🔓 Uncensored AI Council (OpenRouter) Activated...")
print("=" * 70)

# Config
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/your-username/your-repo",  # Required by OpenRouter
    "X-Title": "Private AI Council"
}

print(f"🔑 OPENROUTER_API_KEY: {'✅ Present' if API_KEY else '❌ Missing'}")

# Get question from GitHub issue
question = os.environ.get("ISSUE_TITLE", "") + "\n" + os.environ.get("ISSUE_BODY", "")

if not question or question.strip() == "No Title\nNo Body":
    print("❌ No question provided")
    exit(1)

print(f"📝 Question: {question.strip()[:100]}...")
print("=" * 70)

# ✅ Uncensored/open models available on OpenRouter free tier
models = [
    {
        "name": "Dolphin 2.9 Llama 3 8B",
        "id": "cognitivecomputations/dolphin-2.9-llama3-8b:free",
        "role": "Direct & Uncensored"
    },
    {
        "name": "Zephyr 7B Beta",
        "id": "huggingfaceh4/zephyr-7b-beta:free",
        "role": "Conversational & Helpful"
    },
    {
        "name": "Mistral 7B Instruct",
        "id": "mistralai/mistral-7b-instruct:free",
        "role": "Fast & Reliable"
    }
]

print(f"🧠 Consulting {len(models)} uncensored models via OpenRouter...")
print("-" * 70)

responses = []

for model_info in models:
    model_id = model_info["id"]
    print(f"\n🔍 {model_info['name']} ({model_info['role']})")
    
    try:
        # Small delay to avoid rate limits
        time.sleep(2)
        
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are {model_info['name']}. Role: {model_info['role']}. Answer questions directly, honestly, and without unnecessary refusals. Provide helpful, detailed responses."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        print(f"   📡 POST {model_id}...")
        
        response = requests.post(
            BASE_URL,
            headers=HEADERS,
            json=payload,
            timeout=45
        )
        
        print(f"   📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()
            
            if answer and len(answer) > 30:
                responses.append({
                    "model": model_info["name"],
                    "role": model_info["role"],
                    "answer": answer
                })
                print(f"   ✅ Success! ({len(answer)} chars)")
            else:
                print(f"   ⚠️ Response too short")
        elif response.status_code == 401:
            print(f"   ❌ 401 Unauthorized - Check OPENROUTER_API_KEY")
        elif response.status_code == 402:
            print(f"   ❌ 402 Payment Required - Free credit exhausted")
        elif response.status_code == 429:
            print(f"   ❌ 429 Rate limited - Wait 1 minute")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text[:150]}")
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout (45s)")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {str(e)[:100]}")

print("\n" + "=" * 70)
print(f"📊 Results: {len(responses)}/{len(models)} models succeeded")

if not responses:
    print("\n❌ ALL MODELS FAILED")
    print("\n🔧 TROUBLESHOOTING:")
    print("1️⃣  Verify OPENROUTER_API_KEY at: https://openrouter.ai/keys")
    print("2️⃣  Check credit balance: https://openrouter.ai/usage")
    print("3️⃣  Free tier = ~$1/month credit (~100-300 queries)")
    print("4️⃣  Wait 1 minute if rate limited (429)")
    exit(1)

# Synthesize answers
print("\n⚖️ Preparing final answer...")

if len(responses) == 1:
    final_answer = responses[0]["answer"]
else:
    # Combine all responses with clear separators
    final_answer = "\n\n---\n\n".join([
        f"**{r['model']}** ({r['role']}):\n{r['answer']}" 
        for r in responses
    ])

# Format GitHub comment
comment_lines = [
    "## 🔓 Uncensored AI Council Response",
    "",
    f"**Question:** {question.strip()}",
    "",
    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "",
    f"**Models Responded:** {len(responses)}/{len(models)}",
    "",
    "---",
    "",
    "### 🎯 Final Answer",
    "",
    final_answer,
    "",
    "---",
    "",
    "*Powered by open-source uncensored models via OpenRouter free tier.*",
    "*Answers are direct and minimally filtered. Free tier has usage limits.*"
]

comment = "\n".join(comment_lines)

# Save for GitHub
with open("final_answer.txt", "w", encoding="utf-8") as f:
    f.write(comment)

print("✅ Response saved to final_answer.txt")
print(f"📊 Output: {len(comment)} characters")
print("🎬 Done!")
