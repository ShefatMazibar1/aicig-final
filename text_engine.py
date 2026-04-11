"""
Text Engine - AICIG Final System
Handles all text generation via Hugging Face Inference API.
"""

import os
import time
from huggingface_hub import InferenceClient


class TextEngine:
    def __init__(self, hf_token=None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")
        self.client = InferenceClient(api_key=self.token)

    def generate(self, prompt, model_id, max_tokens=300, temperature=0.7,
                 top_p=0.9, repetition_penalty=1.1):
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that generates high-quality written content. Be clear, creative, and thorough."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            text = response.choices[0].message.content.strip()
            return text, time.time() - start
        except Exception as e:
            return f"Error: {str(e)}", time.time() - start
