import os
import time
from typing import Optional, Tuple
import requests
from PIL import Image
import io
import base64

class ImageEngine:
    HF_SPACE_URL = "https://shef370-ai-content-generator.hf.space"

    def __init__(self, hf_token: Optional[str] = None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")

    def _enhance_prompt(self, prompt: str) -> str:
        quality_keywords = ["detailed", "4k", "high quality", "realistic",
                           "digital art", "oil painting", "photorealistic"]
        if not any(k in prompt.lower() for k in quality_keywords):
            return prompt + ", highly detailed, high quality, sharp focus"
        return prompt

    def generate(self, prompt: str, model_id: str, width: int = 512, 
                 height: int = 512, steps: int = 25, **kwargs) -> Tuple[Optional[Image.Image], float, str]:
        
        enhanced = self._enhance_prompt(prompt)
        start = time.time()
        
        api_url = f"{self.HF_SPACE_URL}/api/predict"
        payload = {
            "fn_index": 0,
            "data": [enhanced, width, height, steps],
            "session_hash": "aicig_session"
        }

        try:
            response = requests.post(api_url, json=payload, timeout=180)
            elapsed = time.time() - start

            if response.status_code == 200:
                result = response.json()
                if 'data' in result and len(result['data']) >= 2:
                    image_data = result['data'][0]
                    info = result['data'][1]
                    
                    if isinstance(image_data, str):
                        if image_data.startswith('data:image'):
                            image_data = image_data.split(',')[1]
                        img_bytes = base64.b64decode(image_data)
                        image = Image.open(io.BytesIO(img_bytes))
                        return image, elapsed, f"Success: {info}"
                    
                    elif image_data is None:
                        return None, elapsed, f"HF error: {info}"
                
                return None, elapsed, "Unexpected response"

            else:
                return None, elapsed, f"HF error {response.status_code}"

        except requests.exceptions.Timeout:
            return None, time.time() - start, "Timeout"
        except Exception as e:
            return None, time.time() - start, f"Error: {str(e)}"
