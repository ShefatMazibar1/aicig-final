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
        if not self.token:
            print("WARNING: No HF_TOKEN provided. Text generation will fail.")
        self.client = InferenceClient(api_key=self.token)

    def generate(self, prompt, model_id, max_tokens=300, temperature=0.7,
                 top_p=0.9, repetition_penalty=1.1):
        if not self.token:
            return "Error: HF_TOKEN not configured", 0
            
        start = time.time()
        try:
            print(f"Generating text with model: {model_id}")
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
            elapsed = time.time() - start
            print(f"Text generated in {elapsed:.2f}s")
            return text, elapsed
        except Exception as e:
            elapsed = time.time() - start
            error_msg = str(e)
            print(f"Text generation error: {error_msg}")
            if "401" in error_msg:
                return f"Error: Invalid HF_TOKEN. Please check your Hugging Face token. ({error_msg})", elapsed
            elif "503" in error_msg:
                return f"Error: Model is loading or unavailable. Please try again in a moment. ({error_msg})", elapsed
            elif "429" in error_msg:
                return f"Error: Rate limit exceeded. Please wait a moment. ({error_msg})", elapsed
            else:
                return f"Error: {error_msg}", elapsed
