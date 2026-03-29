import os
from groq import Groq
from datetime import datetime

print("🤖 Top-Tier AI Council (Groq) - 2 Model Edition")
print("=" * 70)

# Initialize Groq client
client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Get question from GitHub issue
question = os.environ.get("ISSUE_TITLE", "") + "\n" + os.environ.get("ISSUE_BODY", "")

if not question or question.strip() == "No Title\nNo Body":
    print("❌ No question provided")
    exit(1)

print(f"📝 Question: {question.strip()[:100]}...")
print("=" * 70)

# ✅ ONLY THE 2 STABLE MODELS
models = [
    {
        "name": "Llama 3.1 8B",
        "id": "llama-3.1-8b-instant",
        "role": "Fast & Concise"
    },
    {
        "name": "Llama 3.3 70B",
        "id": "llama-3.3-70b-versatile", 
        "role": "Powerful & Detailed"
    },
    {
    "name": "Mixtral 8x7B",
    "id": "mixtral-8x7b-32768", 
    "role": "Creative & Analytical"
}
]

print(f"🧠 Consulting {len(models)} stable models via Groq...")
print("-" * 70)

responses = []

for model_info in models:
    try:
        print(f"  Asking {model_info['name']} ({model_info['role']})...")
        
        completion = client.chat.completions.create(
            model=model_info["id"],
            messages=[
                {
                    "role": "system",
                    "content": f"You are {model_info['name']}. Role: {model_info['role']}. Provide helpful, accurate, well-formatted responses."
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        answer = completion.choices[0].message.content.strip()
        
        if answer and len(answer) > 30:
            responses.append({
                "model": model_info["name"],
                "role": model_info["role"],
                "answer": answer
            })
            print(f"    ✅ Success! ({len(answer)} chars)")
        else:
            print(f"    ⚠️ Response too short")
            
    except Exception as e:
        print(f"    ❌ Error: {str(e)[:100]}")

print("\n" + "=" * 70)
print(f"📊 Results: {len(responses)}/{len(models)} models succeeded")

if not responses:
    print("\n❌ ALL MODELS FAILED")
    print("\n🔧 Check GROQ_API_KEY at: https://console.groq.com/keys")
    exit(1)

# Synthesize answers
print("\n⚖️ Synthesizing final answer...")

if len(responses) == 1:
    final_answer = responses[0]["answer"]
else:
    # Use Llama 3.3 70B to synthesize (most powerful)
    try:
        synthesis_prompt = f"""Combine these two AI responses into ONE clear, comprehensive answer.

QUESTION: {question}

RESPONSE 1 ({responses[0]['model']}):
{responses[0]['answer']}

RESPONSE 2 ({responses[1]['model']}):
{responses[1]['answer']}

Provide the final unified answer below:"""
        
        synth = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Synthesize two AI perspectives into one clear, actionable answer."},
                {"role": "user", "content": synthesis_prompt}
            ],
            max_tokens=1000
        )
        final_answer = synth.choices[0].message.content.strip()
    except:
        # Fallback: simple concatenation
        final_answer = "\n\n---\n\n".join([f"**{r['model']}**:\n{r['answer']}" for r in responses])

# Format GitHub comment
comment_lines = [
    "## 🤖 AI Council Response",
    "",
    f"**Question:** {question.strip()}",
    "",
    f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
    "",
    f"**Models:** {[r['model'] for r in responses]}",
    "",
    "---",
    "",
    "### 🎯 Final Answer",
    "",
    final_answer,
    "",
    "---",
    "",
    "### 📊 Individual Responses",
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
comment_lines.append("*Powered by Groq free tier • Llama 3.1 8B + Llama 3.3 70B • Fast, reliable, free forever*")

comment = "\n".join(comment_lines)

# Save for GitHub
with open("final_answer.txt", "w", encoding="utf-8") as f:
    f.write(comment)

print("✅ Response saved to final_answer.txt")
print(f"📊 Output: {len(comment)} characters")
print("🎬 Done!")
