"""
Image Engine - AICIG Final System
Calls Hugging Face Space for image generation (reliable free CPU).
"""

import os
import time
from typing import Optional, Tuple
import requests
from PIL import Image
import io
import base64


class ImageEngine:
    """
    Uses Hugging Face Space for image generation.
    Space URL: https://shef370-ai-content-generator.hf.space
    """
    
    # Your HF Space URL
    HF_SPACE_URL = "https://shef370-ai-content-generator.hf.space"

    def __init__(self, hf_token: Optional[str] = None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")

    def _enhance_prompt(self, prompt: str) -> str:
        quality_keywords = ["detailed", "4k", "high quality", "realistic",
                           "digital art", "oil painting", "photorealistic"]
        if not any(k in prompt.lower() for k in quality_keywords):
            return prompt + ", highly detailed, high quality, sharp focus"
        return prompt

    def generate(
        self,
        prompt: str,
        model_id: str,  # Not used but kept for compatibility
        width: int = 512,
        height: int = 512,
        steps: int = 25,
        guidance_scale: float = 7.5,
        negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy",
        retries: int = 2,
    ) -> Tuple[Optional[Image.Image], float, str]:
        """
        Call HF Space API for image generation.
        """
        enhanced = self._enhance_prompt(prompt)
        start = time.time()
        
        # HF Space Gradio API endpoint
        api_url = f"{self.HF_SPACE_URL}/api/predict"
        
        payload = {
            "fn_index": 0,  # First function in your Gradio app
            "data": [enhanced, width, height, steps],
            "session_hash": "aicig_session"
        }

        try:
            print(f"Calling HF Space: {api_url}")
            
            response = requests.post(
                api_url,
                json=payload,
                timeout=300  # 5 minutes - CPU generation takes time!
            )
            
            elapsed = time.time() - start

            if response.status_code == 200:
                result = response.json()
                
                # Gradio returns data in 'data' field
                if 'data' in result and len(result['data']) >= 2:
                    image_data = result['data'][0]
                    info = result['data'][1]
                    
                    if isinstance(image_data, str):
                        # Base64 encoded image
                        if image_data.startswith('data:image'):
                            # Remove data URL prefix
                            image_data = image_data.split(',')[1]
                        
                        img_bytes = base64.b64decode(image_data)
                        image = Image.open(io.BytesIO(img_bytes))
                        return image, elapsed, f"Success: {info}"
                    
                    elif image_data is None:
                        # Error in generation
                        return None, elapsed, f"HF Space error: {info}"
                
                return None, elapsed, "Unexpected response format from HF Space"

            else:
                error_text = response.text[:200]
                print(f"HF Space error {response.status_code}: {error_text}")
                return None, elapsed, f"HF Space API error: {response.status_code}"

        except requests.exceptions.Timeout:
            return None, time.time() - start, "HF Space timeout (generation took too long)"
            
        except Exception as e:
            return None, time.time() - start, f"HF Space exception: {str(e)}"
