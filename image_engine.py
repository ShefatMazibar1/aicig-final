"""
Image Engine - AICIG Final System
Handles image generation via Replicate API (more reliable than HF for images).
"""

import os
import time
from typing import Optional, Tuple
import requests


class ImageEngine:
    """
    Manages image generation using Replicate API.
    Replicate has a free tier and more reliable image generation.
    """

    REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"

    def __init__(self, replicate_token: Optional[str] = None):
        # Try REPLICATE_TOKEN first, then HF_TOKEN as fallback
        self.token = replicate_token or os.environ.get("REPLICATE_TOKEN") or os.environ.get("HF_TOKEN", "")
        if not self.token:
            print("WARNING: No REPLICATE_TOKEN or HF_TOKEN provided. Image generation will fail.")
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

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
    ) -> Tuple[Optional[any], float, str]:
        """
        Generate an image using Replicate API.
        Returns (image URL or None, duration_seconds, status_message).
        """
        if not self.token:
            return None, 0, "Error: REPLICATE_TOKEN not configured. Get free token at replicate.com/account/api-tokens"
        
        enhanced = self._enhance_prompt(prompt)
        start = time.time()
        
        # Map model IDs to Replicate models
        replicate_models = {
            "runwayml/stable-diffusion-v1-5": "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21a5835157c3e9f2a",
            "stabilityai/stable-diffusion-2-1": "stability-ai/stable-diffusion-2-1:5c7d4dc6dd3bf575161f47f82a7ee0d9b5f2c5b4b0e8e6b6e6b6e6b6e6b6e6b",  # Placeholder
            "stabilityai/stable-diffusion-xl-base-1.0": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        }
        
        # Use mapped model or default to SD v1.5
        version = replicate_models.get(model_id, replicate_models["runwayml/stable-diffusion-v1-5"])
        
        # Create prediction
        payload = {
            "version": version,
            "input": {
                "prompt": enhanced,
                "negative_prompt": negative_prompt,
                "num_inference_steps": min(steps, 50),
                "guidance_scale": guidance_scale,
                "width": width,
                "height": height,
            }
        }

        try:
            print(f"Creating Replicate prediction for: {enhanced[:50]}...")
            
            # Start prediction
            response = requests.post(
                self.REPLICATE_API_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 201:
                error_text = response.text[:200]
                print(f"Replicate error {response.status_code}: {error_text}")
                return None, time.time() - start, f"Replicate API error: {response.status_code}"
            
            prediction = response.json()
            prediction_id = prediction["id"]
            print(f"Prediction started: {prediction_id}")
            
            # Poll for result (max 2 minutes)
            max_wait = 120
            poll_interval = 1
            
            for _ in range(max_wait):
                time.sleep(poll_interval)
                
                status_response = requests.get(
                    f"{self.REPLICATE_API_URL}/{prediction_id}",
                    headers=self.headers,
                    timeout=10
                )
                
                if status_response.status_code != 200:
                    continue
                
                result = status_response.json()
                status = result.get("status")
                
                if status == "succeeded":
                    output = result.get("output")
                    if output:
                        # Replicate returns a list of URLs, take the first one
                        if isinstance(output, list) and len(output) > 0:
                            image_url = output[0]
                        else:
                            image_url = output
                        
                        elapsed = time.time() - start
                        print(f"Image generated in {elapsed:.2f}s: {image_url[:50]}...")
                        return image_url, elapsed, "Success"
                    else:
                        return None, time.time() - start, "No output from Replicate"
                
                elif status == "failed":
                    error = result.get("error", "Unknown error")
                    return None, time.time() - start, f"Replicate generation failed: {error}"
                
                elif status == "canceled":
                    return None, time.time() - start, "Generation was canceled"
                
                # Still processing, continue polling
            
            # Timeout
            return None, time.time() - start, "Generation timed out (took too long)"
            
        except Exception as e:
            elapsed = time.time() - start
            error_msg = str(e)
            print(f"Replicate exception: {error_msg}")
            return None, elapsed, f"Error: {error_msg}"
