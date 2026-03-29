import os
import requests
import time
from datetime import datetime

print("🔓 Uncensored AI Council (OpenRouter) - SIMPLIFIED")
print("=" * 70)

# Config
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/your-username/your-repo",
    "X-Title": "Private AI Council"
}

print(f"🔑 API Key: {'✅ Present' if API_KEY else '❌ Missing'}")

# Get question
question = os.environ.get("ISSUE_TITLE", "") + "\n" + os.environ.get("ISSUE_BODY", "")
print(f"📝 Question: {question.strip()[:100]}...")
print("=" * 70)

# ✅ START WITH JUST ONE CONFIRMED WORKING MODEL
# Go to https://openrouter.ai/models?max_price=0 to verify current IDs
# Backup options (test one at a time)
models = [
    {"name": "Nous Hermes 3", "id": "nousresearch/nous-hermes-3-405b-instruct:free", "role": "Less Filtered"},
    {"name": "Qwen3 4B", "id": "qwen/qwen3-4b:free", "role": "Direct"},
    {"name": "Llama 3.3 70B", "id": "meta-llama/llama-3.3-70b-instruct:free", "role": "Powerful"}
]

print(f"🧠 Consulting {len(models)} model(s)...")
print("-" * 70)

responses = []

for model_info in models:
    model_id = model_info["id"]
    print(f"\n🔍 {model_info['name']} ({model_info['role']})")
    
    try:
        # ✅ LONGER DELAY to avoid rate limits (free tier is strict)
        print("   ⏳ Waiting 10s to avoid rate limits...")
        time.sleep(10)
        
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer directly and honestly without filters."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "max_tokens": 600,
            "temperature": 0.7
        }
        
        print(f"   📡 POST {model_id}...")
        
        response = requests.post(
            BASE_URL,
            headers=HEADERS,
            json=payload,
            timeout=60  # Longer timeout
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
                print(f"   ✅ SUCCESS! ({len(answer)} chars)")
            else:
                print(f"   ⚠️ Response too short")
        elif response.status_code == 429:
            print(f"   ❌ 429 Rate limited - FREE TIER LIMIT REACHED")
            print(f"   💡 Wait 1 hour or add $5 for more queries")
        elif response.status_code == 400:
            print(f"   ❌ 400 Invalid model ID")
            print(f"   💡 Check exact ID at: https://openrouter.ai/models?max_price=0")
        elif response.status_code == 401:
            print(f"   ❌ 401 Unauthorized - Check API key")
        elif response.status_code == 402:
            print(f"   ❌ 402 Payment Required - Free credit exhausted")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text[:150]}")
            
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {str(e)[:100]}")

print("\n" + "=" * 70)
print(f"📊 Results: {len(responses)}/{len(models)} succeeded")

if not responses:
    print("\n❌ FAILED")
    print("\n🔧 NEXT STEPS:")
    print("1️⃣  Wait 1 hour (free tier rate limit resets)")
    print("2️⃣  OR check exact model ID at: https://openrouter.ai/models?max_price=0")
    print("3️⃣  OR add $5 to your OpenRouter account for unlimited queries")
    exit(1)

# Format answer
final_answer = responses[0]["answer"]

comment_lines = [
    "## 🔓 Uncensored AI Response",
    "",
    f"**Question:** {question.strip()}",
    "",
    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "",
    f"**Model:** {responses[0]['model']}",
    "",
    "---",
    "",
    final_answer,
    "",
    "---",
    "*Via OpenRouter free tier • Venice Uncensored model*"
]

comment = "\n".join(comment_lines)

with open("final_answer.txt", "w", encoding="utf-8") as f:
    f.write(comment)

print("✅ Response saved!")
print("🎬 Done!")
