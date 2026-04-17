"""
Text Engine - AICIG Final System
Uses Groq API - completely free tier, no credit card needed.
Sign up at console.groq.com
"""
import os
import time
import requests


class TextEngine:
    def __init__(self, hf_token=None):
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.hf_token = hf_token or os.environ.get("HF_TOKEN", "")

    def generate(self, prompt, model_id, max_tokens=300, temperature=0.7,
                 top_p=0.9, repetition_penalty=1.1):

        if self.groq_key:
            return self._generate_groq(prompt, max_tokens, temperature, top_p)

        return "Error: GROQ_API_KEY not set. Get free key at console.groq.com", 0

    def _generate_groq(self, prompt, max_tokens, temperature, top_p):
        start = time.time()
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",  # Free Groq model
                    "messages": [
                        {"role": "system", "content": "You are a helpful AI assistant that generates high-quality written content. Be creative, clear and thorough."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": min(temperature, 1.0),
                    "top_p": top_p,
                },
                timeout=30,
            )
            elapsed = time.time() - start
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"].strip()
                print(f"Groq generated in {elapsed:.2f}s")
                return text, elapsed
            else:
                return f"Error: {resp.status_code} - {resp.text[:200]}", elapsed
        except Exception as e:
            return f"Error: {str(e)}", time.time() - start
