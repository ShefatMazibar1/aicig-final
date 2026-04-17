"""
Image Engine - AICIG Final System
Uses Pollinations.ai - completely free, no API key needed.
"""
import time
import requests
from PIL import Image
import io


class ImageEngine:
    def __init__(self, token=None):
        pass  # No token needed

    def generate(self, prompt, model_id=None, width=512, height=512, steps=20,
                 guidance_scale=7.5, negative_prompt="blurry, low quality", retries=2):
        start = time.time()
        try:
            enhanced = prompt + ", highly detailed, high quality, sharp focus"
            
            # Clean prompt for URL
            url_prompt = requests.utils.quote(enhanced)
            
            url = (
                f"https://image.pollinations.ai/prompt/{url_prompt}"
                f"?width={width}&height={height}&seed=42&nologo=true&enhance=true"
            )

            print(f"Calling Pollinations: {url[:80]}...")

            resp = requests.get(url, timeout=60)
            elapsed = time.time() - start

            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                image = Image.open(io.BytesIO(resp.content))
                print(f"Image generated in {elapsed:.1f}s")
                return image, elapsed, "Success"
            else:
                return None, elapsed, f"Error {resp.status_code}: {resp.text[:100]}"

        except requests.Timeout:
            return None, time.time() - start, "Timeout - try again"
        except Exception as e:
            return None, time.time() - start, f"Error: {str(e)}"
