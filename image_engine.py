"""
Image Engine - AICIG Final System
Handles image generation via Hugging Face Inference API.
"""

import os
import io
import time
import requests
import base64
from PIL import Image
from typing import Optional, Tuple


class ImageEngine:
    """
    Manages image generation using Hugging Face Inference API.
    """

    def __init__(self, hf_token: Optional[str] = None):
        self.token = hf_token or os.environ.get("HF_TOKEN", "")
        if not self.token:
            print("WARNING: No HF_TOKEN provided. Image generation will fail.")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
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
    ) -> Tuple[Optional[Image.Image], float, str]:
        """
        Generate an image from a prompt.
        Returns (PIL Image or None, duration_seconds, status_message).
        """
        if not self.token:
            return None, 0, "Error: HF_TOKEN not configured"
        
        enhanced = self._enhance_prompt(prompt)
        start = time.time()
        
        # Try using the Hugging Face Inference API with binary response
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        
        # Simple payload - just the prompt with basic parameters
        payload = {
            "inputs": enhanced,
            "parameters": {
                "num_inference_steps": min(steps, 25),  # Cap at 25 for free tier
                "guidance_scale": guidance_scale,
                "negative_prompt": negative_prompt,
            }
        }

        for attempt in range(retries):
            try:
                print(f"Image generation attempt {attempt + 1}/{retries}...")
                
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=180  # 3 minute timeout
                )
                
                elapsed = time.time() - start

                # Check if we got an image back
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    # Direct image response
                    if 'image' in content_type:
                        try:
                            image = Image.open(io.BytesIO(response.content))
                            print(f"Image generated successfully in {elapsed:.2f}s")
                            return image, elapsed, "Success"
                        except Exception as e:
                            print(f"Error opening image: {e}")
                            return None, elapsed, f"Error opening image: {e}"
                    
                    # JSON response with base64 image
                    try:
                        data = response.json()
                        
                        # Handle different response formats
                        if isinstance(data, list) and len(data) > 0:
                            # Format: [{"image": "base64..."}] or just ["base64..."]
                            img_data = data[0]
                            if isinstance(img_data, dict) and 'image' in img_data:
                                img_bytes = base64.b64decode(img_data['image'])
                            elif isinstance(img_data, str):
                                img_bytes = base64.b64decode(img_data)
                            else:
                                raise ValueError(f"Unexpected response format: {type(img_data)}")
                                
                            image = Image.open(io.BytesIO(img_bytes))
                            return image, elapsed, "Success"
                            
                        elif isinstance(data, dict):
                            # Format: {"image": "base64..."}
                            if 'image' in data:
                                img_bytes = base64.b64decode(data['image'])
                                image = Image.open(io.BytesIO(img_bytes))
                                return image, elapsed, "Success"
                                
                    except Exception as e:
                        print(f"Error parsing JSON response: {e}")
                        # Try to open as raw image anyway
                        try:
                            image = Image.open(io.BytesIO(response.content))
                            return image, elapsed, "Success"
                        except:
                            pass

                elif response.status_code == 503:
                    # Model is loading - wait and retry
                    wait_time = 20
                    try:
                        error_data = response.json()
                        wait_time = error_data.get("estimated_time", 20)
                    except:
                        pass
                    
                    print(f"Model loading, waiting {wait_time:.0f} seconds...")
                    time.sleep(min(wait_time, 60))
                    continue  # Retry

                elif response.status_code == 429:
                    # Rate limited
                    print(f"Rate limited, waiting 10 seconds...")
                    time.sleep(10)
                    continue

                else:
                    # Other error
                    error_text = response.text[:200]
                    print(f"Error {response.status_code}: {error_text}")
                    
                    # If payload error, try simpler version
                    if response.status_code == 422 and attempt == 0:
                        print("Trying simpler payload...")
                        payload = {"inputs": enhanced}
                        continue

            except requests.exceptions.Timeout:
                print(f"Request timeout on attempt {attempt + 1}")
                if attempt < retries - 1:
                    time.sleep(5)
                continue
                
            except Exception as e:
                print(f"Exception on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
                continue

        # All retries failed
        total_time = time.time() - start
        return None, total_time, "Image generation failed after all retries. The model may be unavailable on the free Inference API tier. Try using 'stable-diffusion-v1-5' model or check your HF_TOKEN permissions."
