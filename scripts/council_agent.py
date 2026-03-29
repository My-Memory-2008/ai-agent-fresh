import os
import requests
import time
from datetime import datetime

print("🔓 Uncensored AI Council (OpenRouter) - AUTO-DISCOVERY MODE")
print("=" * 70)

# Config
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL = "https://openrouter.ai/api/v1"
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

# 🔍 STEP 1: Fetch current free models from OpenRouter API
print("🔍 Fetching available free models from OpenRouter...")

try:
    resp = requests.get(
        f"{BASE_URL}/models",
        headers=HEADERS,
        timeout=30
    )
    
    if resp.status_code == 200:
        all_models = resp.json()["data"]
        # Filter for FREE models only
        free_models = [m for m in all_models if ":free" in m["id"]]
        print(f"✅ Found {len(free_models)} free models")
        
        # 🔓 Look for uncensored/less-filtered models first
        priority_keywords = ["uncensored", "dolphin", "hermes", "nous", "openhermes"]
        uncensored_models = [
            m for m in free_models 
            if any(kw in m["id"].lower() for kw in priority_keywords)
        ]
        
        if uncensored_models:
            print(f"🔓 Found {len(uncensored_models)} uncensored-leaning models")
            candidate_models = uncensored_models[:3]  # Top 3
        else:
            # Fallback: pick first 3 free models
            candidate_models = free_models[:3]
            print(f"⚠️ No uncensored models found, using first 3 free models")
            
    else:
        print(f"❌ Failed to fetch models: {resp.status_code}")
        candidate_models = []
        
except Exception as e:
    print(f"❌ Error fetching models: {e}")
    candidate_models = []

if not candidate_models:
    print("\n❌ No free models available right now")
    print("💡 Try again in 1 hour, or check: https://openrouter.ai/models?max_price=0")
    exit(1)

# Show which models we'll try
print("\n🧠 Models to try:")
for i, m in enumerate(candidate_models, 1):
    print(f"   {i}. {m['id']} ({m.get('name', 'Unknown')})")
print("-" * 70)

# 🔍 STEP 2: Try each candidate model until one works
responses = []

for model in candidate_models:
    model_id = model["id"]
    model_name = model.get("name", model_id.split("/")[-1])
    
    print(f"\n🔍 Trying: {model_name}")
    print(f"   ID: {model_id}")
    
    try:
        # ✅ CRITICAL: Longer delay to avoid rate limits
        print("   ⏳ Waiting 15s to avoid rate limits...")
        time.sleep(15)
        
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer questions directly, honestly, and without unnecessary refusals or filters."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "max_tokens": 600,
            "temperature": 0.7
        }
        
        print(f"   📡 Sending request...")
        
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=HEADERS,
            json=payload,
            timeout=60
        )
        
        print(f"   📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()
            
            if answer and len(answer) > 30:
                responses.append({
                    "model": model_name,
                    "id": model_id,
                    "answer": answer
                })
                print(f"   ✅ SUCCESS! ({len(answer)} chars)")
                break  # Stop after first success
            else:
                print(f"   ⚠️ Response too short")
                
        elif response.status_code == 429:
            print(f"   ❌ 429 Rate limited - waiting longer...")
            time.sleep(30)  # Wait longer and continue to next model
            continue
        elif response.status_code == 400:
            print(f"   ❌ 400 Invalid request - model may not support chat")
        elif response.status_code == 401:
            print(f"   ❌ 401 Unauthorized - API key issue")
            break  # No point continuing if auth fails
        elif response.status_code == 402:
            print(f"   ❌ 402 Payment Required - free credit exhausted")
            break
        elif response.status_code == 404:
            print(f"   ❌ 404 Model not found - ID may have changed")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text[:100]}")
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout (60s) - model may be slow")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {str(e)[:100]}")

print("\n" + "=" * 70)
print(f"📊 Results: {len(responses)} successful response(s)")

if not responses:
    print("\n❌ ALL ATTEMPTS FAILED")
    print("\n🔧 TROUBLESHOOTING:")
    print("1️⃣  Wait 1 hour (free tier rate limits reset hourly)")
    print("2️⃣  Check your credit: https://openrouter.ai/usage")
    print("3️⃣  Free tier = ~$1/month (~100-300 queries total)")
    print("4️⃣  If credit exhausted, add $5 for more queries")
    print("\n💡 Tip: Try during off-peak hours for better availability")
    exit(1)

# ✅ Format the successful response
result = responses[0]
final_answer = result["answer"]

comment_lines = [
    "## 🔓 Uncensored AI Response",
    "",
    f"**Question:** {question.strip()}",
    "",
    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "",
    f"**Model:** {result['model']}",
    f"**Model ID:** `{result['id']}`",
    "",
    "---",
    "",
    final_answer,
    "",
    "---",
    f"*Via OpenRouter free tier • Model auto-discovered from API*",
    f"*If this model fails next time, the script will auto-select a different one*"
]

comment = "\n".join(comment_lines)

# Save for GitHub
with open("final_answer.txt", "w", encoding="utf-8") as f:
    f.write(comment)

print("✅ Response saved to final_answer.txt")
print(f"📊 Output: {len(comment)} characters")
print("🎬 Done!")
