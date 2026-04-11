"""
Image Engine - AICIG Final System
Handles image generation via Hugging Face Inference API.
"""

import os
import io
import time
import requests
from PIL import Image
from typing import Optional


HF_API_URL = "https://api-inference.huggingface.co/models/"


class ImageEngine:
    """
    Manages image generation using Hugging Face Inference API
    with Stable Diffusion and compatible diffusion models.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")
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
        num_inference_steps: int = 25,
        guidance_scale: float = 7.5,
        negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy",
        retries: int = 3,
    ) -> tuple[Optional[Image.Image], float]:
        """
        Generate an image from a prompt.
        Returns (PIL Image or None, duration_seconds).
        """
        enhanced = self._enhance_prompt(prompt)
        payload = {
            "inputs": enhanced,
            "parameters": {
                "num_inference_steps": num_inference_steps,
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

        for attempt in range(retries):
            try:
                resp = requests.post(
                    url, headers=self.headers, json=payload, timeout=120
                )
                duration = time.time() - start

                if resp.status_code == 200:
                    try:
                        img = Image.open(io.BytesIO(resp.content))
                        return img, duration
                    except Exception:
                        return None, duration

                elif resp.status_code == 503:
                    wait = 20
                    try:
                        wait = resp.json().get("estimated_time", 20)
                    except Exception:
                        pass
                    time.sleep(min(wait, 40))
                    continue

                else:
                    return None, time.time() - start

            except requests.exceptions.Timeout:
                if attempt == retries - 1:
                    return None, time.time() - start
                time.sleep(10)
            except Exception:
                return None, time.time() - start

        return None, time.time() - start
