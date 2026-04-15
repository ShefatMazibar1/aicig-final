"""
Image Engine - AICIG Final System
Handles image generation via Hugging Face Inference API.
Uses the newer InferenceClient for better reliability.
"""

import os
import io
import time
from PIL import Image
from typing import Optional, Tuple
import requests


class ImageEngine:
    """
    Manages image generation using Hugging Face Inference API.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")
        if not self.token:
            print("WARNING: No HF_TOKEN provided. Image generation will fail.")

    def _enhance_prompt(self, prompt: str) -> str:
        """Add quality-boosting suffix if not already detailed."""
        quality_keywords = ["detailed", "4k", "high quality", "realistic",
                           "digital art", "oil painting", "photorealistic"]
        if not any(k in prompt.lower() for k in quality_keywords):
            return prompt + ", highly detailed, high quality, sharp focus"
        return prompt

    def generate(
        self,
        prompt: str,
        model_id: str,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        guidance_scale: float = 7.5,
        negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy",
        retries: int = 3,
    ) -> Tuple[Optional[Image.Image], float, str]:
        """
        Generate an image from a prompt using Hugging Face InferenceClient.
        Returns (PIL Image or None, duration_seconds, status_message).
        """
        if not self.token:
            return None, 0, "Error: HF_TOKEN not configured"
        
        enhanced = self._enhance_prompt(prompt)
        start = time.time()
        
        try:
            # Use InferenceClient which handles the API better
            from huggingface_hub import InferenceClient
            
            client = InferenceClient(api_key=self.token)
            
            print(f"Using InferenceClient for model: {model_id}")
            
            # Generate image using text_to_image
            # This uses the newer API which is more reliable
            image = client.text_to_image(
                enhanced,
                model=model_id,
                num_inference_steps=min(steps, 25),  # Cap at 25 for free tier
                guidance_scale=guidance_scale,
                negative_prompt=negative_prompt,
            )
            
            elapsed = time.time() - start
            print(f"Image generated successfully in {elapsed:.2f}s")
            return image, elapsed, "Success"
            
        except Exception as e:
            error_msg = str(e)
            print(f"InferenceClient failed: {error_msg}")
            
            # Fallback to direct API call
            return self._fallback_api_generate(
                enhanced, model_id, width, height, steps, 
                guidance_scale, negative_prompt, retries, start
            )

    def _fallback_api_generate(
        self, prompt: str, model_id: str, width: int, height: int,
        steps: int, guidance_scale: float, negative_prompt: str,
        retries: int, start_time: float
    ) -> Tuple[Optional[Image.Image], float, str]:
        """Fallback to direct API if InferenceClient fails."""
        
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Try minimal payload first
        payloads = [
            {"inputs": prompt},
            {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": min(steps, 20),
                    "guidance_scale": guidance_scale,
                }
            }
        ]
        
        for attempt in range(retries):
            for payload in payloads:
                try:
                    print(f"Fallback API attempt {attempt + 1}, payload: {list(payload.keys())}")
                    
                    response = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=120
                    )
                    
                    elapsed = time.time() - start_time

                    if response.status_code == 200:
                        try:
                            # Try to open as image directly
                            image = Image.open(io.BytesIO(response.content))
                            return image, elapsed, "Success (fallback)"
                        except Exception as e:
                            print(f"Error opening image: {e}")
                            continue

                    elif response.status_code == 503:
                        # Model loading
                        print(f"Model loading (503), waiting...")
                        time.sleep(20)
                        continue
                        
                    elif response.status_code == 429:
                        print(f"Rate limited (429), waiting 10s...")
                        time.sleep(10)
                        continue
                        
                    else:
                        print(f"Error {response.status_code}: {response.text[:100]}")
                        
                except Exception as e:
                    print(f"Exception: {e}")
                    continue

        total_time = time.time() - start_time
        return None, total_time, "Image generation failed. The Hugging Face free Inference API has strict limits. Consider using Hugging Face Spaces for image generation instead."
