"""
Image Engine - AICIG Final System
Handles image generation via Hugging Face Inference API.
"""

import os
import io
import time
import requests
from PIL import Image
from typing import Optional, Tuple


HF_API_URL = "https://api-inference.huggingface.co/models/"


class ImageEngine:
    """
    Manages image generation using Hugging Face Inference API
    with Stable Diffusion and compatible diffusion models.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")
        if not self.token:
            print("WARNING: No HF_TOKEN provided. Image generation will fail.")
        self.headers = {"Authorization": f"Bearer {self.token}"}

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
    ) -> Tuple[Optional[Image.Image], float]:
        """
        Generate an image from a prompt.
        Returns (PIL Image or None, duration_seconds).
        """
        if not self.token:
            return None, 0
            
        enhanced = self._enhance_prompt(prompt)
        
        # Try different payload formats - some models accept width/height, others don't
        payload = {
            "inputs": enhanced,
            "parameters": {
                "num_inference_steps": steps,
                "guidance_scale": guidance_scale,
                "negative_prompt": negative_prompt,
            },
            "options": {
                "wait_for_model": True,
                "use_cache": False,
            }
        }

        url = HF_API_URL + model_id
        start = time.time()
        print(f"Generating image with model: {model_id}, steps: {steps}")

        for attempt in range(retries):
            try:
                print(f"Attempt {attempt + 1}/{retries}...")
                resp = requests.post(
                    url, 
                    headers=self.headers, 
                    json=payload, 
                    timeout=180  # Increased timeout for image generation
                )
                duration = time.time() - start

                if resp.status_code == 200:
                    try:
                        # Check if response is an image
                        content_type = resp.headers.get('content-type', '')
                        if 'image' in content_type:
                            img = Image.open(io.BytesIO(resp.content))
                            print(f"Image generated successfully in {duration:.2f}s")
                            return img, duration
                        
                        # Try to parse as JSON (some APIs return base64)
                        try:
                            data = resp.json()
                            if isinstance(data, list) and len(data) > 0:
                                # Handle list response
                                if isinstance(data[0], dict) and 'image' in data[0]:
                                    import base64
                                    img_data = base64.b64decode(data[0]['image'])
                                    img = Image.open(io.BytesIO(img_data))
                                    return img, duration
                                elif isinstance(data[0], str):
                                    # Base64 encoded image
                                    import base64
                                    img_data = base64.b64decode(data[0])
                                    img = Image.open(io.BytesIO(img_data))
                                    return img, duration
                            elif isinstance(data, dict):
                                if 'image' in data:
                                    import base64
                                    img_data = base64.b64decode(data['image'])
                                    img = Image.open(io.BytesIO(img_data))
                                    return img, duration
                        except:
                            pass
                        
                        # Try direct image open
                        img = Image.open(io.BytesIO(resp.content))
                        return img, duration
                        
                    except Exception as e:
                        print(f"Error processing image: {e}")
                        return None, duration

                elif resp.status_code == 503:
                    # Model is loading
                    wait = 20
                    try:
                        error_data = resp.json()
                        wait = error_data.get("estimated_time", 20)
                        print(f"Model loading, waiting {wait:.0f}s...")
                    except:
                        print(f"Model loading, waiting 20s...")
                    time.sleep(min(wait, 60))
                    continue

                elif resp.status_code == 401:
                    print(f"Authentication error - invalid HF_TOKEN")
                    return None, time.time() - start

                elif resp.status_code == 429:
                    print(f"Rate limit exceeded")
                    return None, time.time() - start

                else:
                    error_text = resp.text[:200]
                    print(f"Error {resp.status_code}: {error_text}")
                    # If it's a payload error, try simpler format
                    if attempt == 0 and (resp.status_code == 422 or "parameter" in error_text.lower()):
                        print("Trying simpler payload format...")
                        payload = {"inputs": enhanced}  # Simplified payload
                        continue
                    return None, time.time() - start

            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt + 1}")
                if attempt == retries - 1:
                    return None, time.time() - start
                time.sleep(10)
                
            except Exception as e:
                print(f"Exception: {e}")
                return None, time.time() - start

        return None, time.time() - start
