import os
import json
import requests
import time
from datetime import datetime

print("🔓 Uncensored AI Council (Cloud) - HTTP DIRECT MODE")
print("=" * 70)

# Config
HF_TOKEN = os.environ.get("HF_TOKEN", "")
BASE_URL = "https://api-inference.huggingface.co/models"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

print(f"🔑 HF_TOKEN: {'✅ Present' if HF_TOKEN else '❌ Missing'}")

# Get question
question = os.environ.get("ISSUE_TITLE", "") + "\n" + os.environ.get("ISSUE_BODY", "")
print(f"📝 Question: {question.strip()[:100]}...")
print("=" * 70)

# ✅ Models CONFIRMED to work with HF free tier (text-generation task)
models = [
    {
        "name": "Mistral 7B Instruct",
        "id": "mistralai/Mistral-7B-Instruct-v0.2",
        "role": "Fast & Reliable",
        "prompt_format": "chat"  # Uses [INST] format
    },
    {
        "name": "Zephyr 7B Beta", 
        "id": "HuggingFaceH4/zephyr-7b-beta",
        "role": "Conversational",
        "prompt_format": "chat"  # Uses <|user|> format
    },
    {
        "name": "Falcon 7B Instruct",
        "id": "tiiuae/falcon-7b-instruct",
        "role": "Direct & Clear",
        "prompt_format": "simple"  # Simple prompt
    }
]

print(f"🧠 Consulting {len(models)} models via direct HTTP...")
print("-" * 70)

responses = []

for model_info in models:
    model_id = model_info["id"]
    print(f"\n🔍 {model_info['name']} ({model_info['role']})")
    
    try:
        # Format prompt based on model type
        if model_info["prompt_format"] == "chat":
            # Chat-style models need special formatting
            prompt = f"<|user|>\n{question}</s>\n<|assistant|>\n"
        else:
            # Simple models
            prompt = f"Question: {question}\n\nAnswer:"
        
        # Payload for text generation
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 600,
                "temperature": 0.7,
                "return_full_text": False,
                "do_sample": True
            },
            "options": {
                "wait_for_model": True,  # Wait if model is loading
                "use_cache": False
            }
        }
        
        print(f"   📡 POST {model_id}...")
        
        # Make direct HTTP request
        response = requests.post(
            f"{BASE_URL}/{model_id}",
            headers=HEADERS,
            json=payload,
            timeout=120  # Longer timeout for cold starts
        )
        
        print(f"   📡 Status: {response.status_code}")
        
        # Handle different response types
        if response.status_code == 200:
            data = response.json()
            
            # Parse response (HF API returns different formats)
            if isinstance(data, list) and len(data) > 0:
                answer = data[0].get("generated_text", "").strip()
            elif isinstance(data, dict) and "generated_text" in data:
                answer = data["generated_text"].strip()
            else:
                answer = str(data)[:500]
            
            if answer and len(answer) > 30:
                responses.append({
                    "model": model_info["name"],
                    "role": model_info["role"],
                    "answer": answer
                })
                print(f"   ✅ Success! ({len(answer)} chars)")
            else:
                print(f"   ⚠️ Response too short: '{answer[:50]}...'")
                
        elif response.status_code == 503:
            # Model is loading - this is normal for free tier
            print(f"   ⏳ Model loading (503). Waiting 30s...")
            time.sleep(30)
            # Retry once
            response2 = requests.post(f"{BASE_URL}/{model_id}", headers=HEADERS, json=payload, timeout=120)
            if response2.status_code == 200:
                data = response2.json()
                if isinstance(data, list) and len(data) > 0:
                    answer = data[0].get("generated_text", "").strip()
                    if len(answer) > 30:
                        responses.append({
                            "model": model_info["name"],
                            "role": model_info["role"], 
                            "answer": answer
                        })
                        print(f"   ✅ Retry success!")
            else:
                print(f"   ❌ Still failed after wait: {response2.status_code}")
                
        elif response.status_code == 401:
            print(f"   ❌ 401 Unauthorized - Check HF_TOKEN")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden - Model may need acceptance")
        elif response.status_code == 429:
            print(f"   ❌ 429 Rate limited - Free tier limit reached")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text[:100]}")
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout (120s) - Model may be slow to load")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error - Check internet/HF status")
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON parse error: {e}")
        print(f"   📄 Raw response: {response.text[:200] if 'response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {type(e).__name__}: {str(e)[:100]}")
    
    # Small delay between requests to avoid rate limits
    time.sleep(2)

print("\n" + "=" * 70)
print(f"📊 Results: {len(responses)}/{len(models)} models succeeded")

if not responses:
    print("\n❌ ALL MODELS FAILED")
    print("\n🔧 TROUBLESHOOTING:")
    print("1️⃣  Verify HF_TOKEN at: https://huggingface.co/settings/tokens")
    print("2️⃣  Ensure token has 'Read' permission checked")
    print("3️⃣  Check HF API status: https://status.huggingface.co")
    print("4️⃣  Free tier has rate limits (~10-30 requests/hour)")
    print("5️⃣  Models may take 30-60s to load on first request")
    print("\n💡 Try again in 10 minutes, or use OpenRouter for more reliability")
    exit(1)

# Synthesize: pick best response or concatenate
print("\n⚖️ Preparing final answer...")

if len(responses) == 1:
    final_answer = responses[0]["answer"]
else:
    # Simple synthesis: combine with separators
    final_answer = "\n\n---\n\n".join([
        f"**{r['model']}** ({r['role']}):\n{r['answer']}" 
        for r in responses
    ])

# Format GitHub comment
comment_parts = [
    "## 🔓 AI Council Response",
    "",
    f"**Question:** {question.strip()}",
    "",
    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "",
    f"**Models Responded:** {len(responses)}/{len(models)}",
    "",
    "---",
    "",
    "### 🎯 Answer",
    "",
    final_answer,
    "",
    "---",
    "",
    "*Powered by open-source models via Hugging Face Inference API (free tier)*"
]

comment = "\n".join(comment_parts)

# Save
with open("final_answer.txt", "w", encoding="utf-8") as f:
    f.write(comment)

print("✅ Response saved to final_answer.txt")
print(f"📊 Output: {len(comment)} characters")
print("🎬 Done!")
