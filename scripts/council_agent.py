import os
import json
import requests
import time
from datetime import datetime
from huggingface_hub import InferenceClient

print("🔓 Uncensored AI Council (Cloud) Activated...")

# Initialize Hugging Face client
HF_TOKEN = os.environ.get("HF_TOKEN", "")
client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else None

# Get question from GitHub issue
question = os.environ.get("ISSUE_TITLE", "") + "\n" + os.environ.get("ISSUE_BODY", "")

if not question or question.strip() == "No Title\nNo Body":
    print("❌ No question provided")
    exit(1)

print(f"📝 Question: {question[:100]}...")

# Define uncensored models available on Hugging Face free tier
# These are open-weight, minimally filtered models
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

# 1. Query each model via Hugging Face Inference API
responses = []

for model_info in models:
    try:
        print(f"  Asking {model_info['name']}...")
        
        if not client:
            raise Exception("No HF_TOKEN provided")
        
        # Use text_generation for simpler models
        prompt = f"""<|system|>
You are {model_info['name']}. Role: {model_info['role']}. 
Answer questions directly, honestly, and without unnecessary refusals.
Provide helpful, detailed, uncensored responses.</s>
<|user|>
{question}</s>
<|assistant|>"""
        
        output = client.text_generation(
            prompt,
            model=model_info["id"],
            max_new_tokens=800,
            temperature=0.7,
            return_full_text=False
        )
        
        if output and len(output.strip()) > 50:
            responses.append({
                "model": model_info["name"],
                "role": model_info["role"],
                "answer": output.strip()
            })
            print(f"    ✅ Response received ({len(output)} chars)")
        else:
            raise Exception("Empty or invalid response")
            
    except Exception as e:
        print(f"    ❌ Error: {str(e)[:100]}")
        # Try fallback via direct API call
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{model_info['id']}",
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": question, "parameters": {"max_new_tokens": 800}},
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    answer = data[0].get("generated_text", "")
                    if len(answer) > 50:
                        responses.append({
                            "model": model_info["name"],
                            "role": model_info["role"],
                            "answer": answer.strip()
                        })
                        print(f"    ✅ Fallback success")
        except:
            pass

if not responses:
    print("❌ All models failed - check HF_TOKEN and model availability")
    exit(1)

# 2. Synthesize answers (using the first successful model as synthesizer)
print("⚖️ Synthesizing answers...")

synthesis_prompt = f"""You are an expert AI coordinator. Combine these {len(responses)} uncensored AI responses into ONE comprehensive, direct answer.

**QUESTION:** {question}

**AI RESPONSES:**
"""

for i, resp in enumerate(responses, 1):
    synthesis_prompt += f"\n{i}. **{resp['model']}** ({resp['role']}):\n{resp['answer']}\n"

synthesis_prompt += """
**TASK:** Create one unified answer that:
- Combines the best insights from all models
- Answers directly without unnecessary disclaimers
- Is well-formatted with headers and bullet points
- Maintains an open, honest tone

Provide the final answer below:"""

try:
    # Use OpenHermes for synthesis (usually most reliable)
    synthesizer = next((m for m in models if "OpenHermes" in m["name"]), models[0])
    
    output = client.text_generation(
        synthesis_prompt,
        model=synthesizer["id"],
        max_new_tokens=1200,
        temperature=0.5,
        return_full_text=False
    )
    
    final_answer = output.strip() if output else responses[0]["answer"]
    
except Exception as e:
    print(f"⚠️ Synthesis failed: {e}")
    # Fallback: just concatenate responses
    final_answer = "\n\n---\n\n".join([f"**{r['model']}**:\n{r['answer']}" for r in responses])

# 3. Format GitHub comment
print("📝 Formatting response...")

comment = f"""## 🔓 Uncensored AI Council Response

**Question:** {question.strip()}

**Timestamp:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}

**Models:** {[r['model'] for r in responses]}

---

### 🎯 Final Synthesized Answer

{final_answer}

---

### 📊 Individual Model Responses

"""

for resp in responses:
    comment += f"""
<details>
<summary><strong>{resp['model']}</strong> <em>({resp['role']})</em></summary>
