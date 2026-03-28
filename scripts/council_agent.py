import os
import json
import requests
import time
from datetime import datetime
from huggingface_hub import InferenceClient

print("🔓 Uncensored AI Council (Cloud) - DEBUG MODE")
print("=" * 60)

# Check HF_TOKEN first
HF_TOKEN = os.environ.get("HF_TOKEN", "")
print(f"🔑 HF_TOKEN present: {bool(HF_TOKEN)}")
if HF_TOKEN:
    print(f"🔑 HF_TOKEN starts with: {HF_TOKEN[:10]}...")
    print(f"🔑 HF_TOKEN length: {len(HF_TOKEN)}")

# Initialize client
client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else None

# Get question
question = os.environ.get("ISSUE_TITLE", "") + "\n" + os.environ.get("ISSUE_BODY", "")
print(f"📝 Question: {question[:100]}...")
print("=" * 60)

# Test with ONE simple model first
test_model = "microsoft/DialoGPT-medium"  # Always available, no acceptance needed
print(f"🧪 Testing connection with: {test_model}")

try:
    if not client:
        raise Exception("Client not initialized - check HF_TOKEN")
    
    output = client.text_generation(
        "Hello, how are you?",
        model=test_model,
        max_new_tokens=50,
        return_full_text=False
    )
    print(f"✅ Test successful! Response: {output[:50]}...")
except Exception as e:
    print(f"❌ Test FAILED: {type(e).__name__}: {str(e)}")
    print("💡 This means your HF_TOKEN or connection has issues.")
    print("💡 Fix: 1) Verify token at https://huggingface.co/settings/tokens")
    print("💡 Fix: 2) Ensure token has 'Read' permission")
    print("💡 Fix: 3) Visit model pages and click 'Agree' if prompted")
    exit(1)

print("=" * 60)

# Now try the uncensored models
models = [
    {
        "name": "Dolphin 2.9 Llama 3 8B",
        "id": "cognitivecomputations/dolphin-2.9-llama3-8b",
        "role": "Direct & Uncensored"
    },
    {
        "name": "OpenHermes 2.5 Mistral 7B",
        "id": "teknium/openhermes-2.5-mistral-7b", 
        "role": "Clear & Helpful"
    },
    {
        "name": "Nous Hermes 2 Mistral 7B",
        "id": "NousResearch/Nous-Hermes-2-Mistral-7B-DPO",
        "role": "Creative & Analytical"
    }
]

print(f"🧠 Consulting {len(models)} uncensored models...")
print("-" * 60)

responses = []

for model_info in models:
    print(f"\n🔍 Trying: {model_info['name']}")
    print(f"   Model ID: {model_info['id']}")
    
    try:
        # Add delay to avoid rate limits
        time.sleep(3)
        
        prompt = f"Answer directly and honestly: {question}"
        
        print("   📡 Sending request...")
        output = client.text_generation(
            prompt,
            model=model_info["id"],
            max_new_tokens=600,
            temperature=0.7,
            return_full_text=False,
            timeout=90  # Longer timeout for cold starts
        )
        
        if output and len(output.strip()) > 30:
            responses.append({
                "model": model_info["name"],
                "role": model_info["role"],
                "answer": output.strip()
            })
            print(f"   ✅ SUCCESS! ({len(output)} chars)")
        else:
            print(f"   ⚠️ Response too short or empty")
            
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"   ❌ FAILED: {error_type}")
        print(f"   💬 Error details: {error_msg[:200]}")
        
        # Check for common issues
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("   💡 Fix: Your HF_TOKEN may be invalid or lack permissions")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            print("   💡 Fix: Visit the model page and click 'Agree and access repository'")
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            print("   💡 Fix: Hugging Face free tier rate limited. Wait 1 hour or try later")
        elif "loading" in error_msg.lower() or "timeout" in error_msg.lower():
            print("   💡 Fix: Model is loading (cold start). Try again in 1-2 minutes")
        elif "not supported" in error_msg.lower():
            print("   💡 Fix: This model may not support text_generation API")

print("\n" + "=" * 60)
print(f"📊 Results: {len(responses)}/{len(models)} models succeeded")

if not responses:
    print("\n❌ ALL MODELS FAILED")
    print("\n🔧 TROUBLESHOOTING STEPS:")
    print("1️⃣  Go to https://huggingface.co/settings/tokens")
    print("    - Verify your token exists and has 'Read' permission")
    print("2️⃣  Visit EACH model page and click 'Agree':")
    for m in models:
        print(f"    - https://huggingface.co/{m['id']}")
    print("3️⃣  Wait 1 hour if you hit rate limits (free tier)")
    print("4️⃣  Try a simpler model first: microsoft/DialoGPT-medium")
    print("\n💡 Alternative: Use OpenRouter API instead of Hugging Face")
    exit(1)

# If we have responses, synthesize them
print("\n⚖️ Synthesizing answers...")

# Simple synthesis: pick the longest response as "best"
best_response = max(responses, key=lambda x: len(x["answer"]))
final_answer = best_response["answer"]

# Format comment
comment_lines = [
    "## 🔓 Uncensored AI Council Response",
    "",
    f"**Question:** {question.strip()}",
    "",
    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "",
    f"**Successful Models:** {[r['model'] for r in responses]}",
    "",
    "---",
    "",
    "### 🎯 Final Answer",
    "",
    final_answer,
    "",
    "---",
    "",
    "### 📊 All Model Responses",
    ""
]

for resp in responses:
    comment_lines.append("<details>")
    comment_lines.append(f"<summary><strong>{resp['model']}</strong> <em>({resp['role']})</em></summary>")
    comment_lines.append("")
    comment_lines.append("```")
    comment_lines.append(resp['answer'])
    comment_lines.append("```")
    comment_lines.append("")
    comment_lines.append("</details>")
    comment_lines.append("")

comment_lines.append("---")
comment_lines.append("*Powered by open-source models via Hugging Face free tier.*")

comment = "\n".join(comment_lines)

# Save
with open("final_answer.txt", "w", encoding="utf-8") as f:
    f.write(comment)

print("✅ Response saved to final_answer.txt")
print(f"📊 Final length: {len(comment)} characters")
