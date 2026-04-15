"""
Model Manager - AICIG Final System
Shefat Mazibar (W1967304) | Supervisor: Jeffrey Ferguson
University of Westminster
"""

import json
import os
from datetime import datetime

DEFAULT_PROFILES = {
    "balanced": {
        "temperature": 0.7, "max_tokens": 300, "top_p": 0.9,
        "repetition_penalty": 1.1,
        "description": "Good balance of creativity and coherence"
    },
    "creative": {
        "temperature": 1.1, "max_tokens": 400, "top_p": 0.95,
        "repetition_penalty": 1.0,
        "description": "More imaginative, less predictable outputs"
    },
    "precise": {
        "temperature": 0.4, "max_tokens": 250, "top_p": 0.8,
        "repetition_penalty": 1.2,
        "description": "Focused, structured, closely follows the prompt"
    },
    "fast": {
        "temperature": 0.7, "max_tokens": 150, "top_p": 0.9,
        "repetition_penalty": 1.1,
        "description": "Quick generation, shorter outputs"
    }
}

AVAILABLE_TEXT_MODELS = {
    "qwen-7b": {
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "display_name": "Qwen 2.5 7B",
        "description": "Strong multilingual model - best quality",
        "strengths": ["articles", "creative writing", "summaries"]
    },
    "llama-8b": {
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "display_name": "Llama 3.1 8B",
        "description": "Meta's fast and capable model",
        "strengths": ["Q&A", "explanations", "descriptions"]
    },
    "deepseek": {
        "model_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "display_name": "DeepSeek R1 7B",
        "description": "Strong reasoning and writing model",
        "strengths": ["reasoning", "structured writing", "analysis"]
    }
}

AVAILABLE_IMAGE_MODELS = {
    "stable-diffusion-v1-5": {
        "model_id": "runwayml/stable-diffusion-v1-5",
        "display_name": "Stable Diffusion v1.5",
        "description": "Fast and reliable via Replicate",
        "strengths": ["general images", "fast"]
    },
    "sdxl-base": {
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "display_name": "Stable Diffusion XL",
        "description": "Higher quality, slower",
        "strengths": ["high quality", "detailed"]
    }
}


class ModelManager:
    """
    Central manager for all AI model configuration, selection,
    and parameter control in the AICIG system.
    """

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.session_start = datetime.now().isoformat()
        self.generation_count = 0

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default_config()

    def _default_config(self):
        return {
            "active_text_model": "qwen-7b",
            "active_image_model": "stable-diffusion-v1-5",
            "active_profile": "balanced",
            "custom_params": {},
            "content_filter": True,
            "save_history": True,
            "created_at": datetime.now().isoformat()
        }

    def save_config(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def get_model_config(self, model_key):
        """Get text model config by key."""
        return AVAILABLE_TEXT_MODELS.get(model_key, AVAILABLE_TEXT_MODELS["qwen-7b"])
    
    def get_image_model_config(self, model_key):
        """Get image model config by key."""
        return AVAILABLE_IMAGE_MODELS.get(model_key, AVAILABLE_IMAGE_MODELS["stable-diffusion-v1-5"])
    
    def get_text_model_keys(self):
        """Return list of text model keys."""
        return list(AVAILABLE_TEXT_MODELS.keys())
    
    def get_image_model_keys(self):
        """Return list of image model keys."""
        return list(AVAILABLE_IMAGE_MODELS.keys())
    
    def get_profile_names(self):
        """Return list of profile names."""
        return list(DEFAULT_PROFILES.keys())
    
    def get_profile(self, profile_name):
        """Get profile parameters - only text generation params."""
        profile = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["balanced"]).copy()
        # Only return params that TextEngine accepts
        text_params = {
            "temperature": profile.get("temperature", 0.7),
            "max_tokens": profile.get("max_tokens", 300),
            "top_p": profile.get("top_p", 0.9),
            "repetition_penalty": profile.get("repetition_penalty", 1.1)
        }
        return text_params
    
    def get_full_config(self):
        """Return full configuration for display."""
        return {
            "text_models": {k: {"name": v["display_name"], "description": v["description"]} 
                          for k, v in AVAILABLE_TEXT_MODELS.items()},
            "image_models": {k: {"name": v["display_name"], "description": v["description"]} 
                           for k, v in AVAILABLE_IMAGE_MODELS.items()},
            "profiles": DEFAULT_PROFILES
        }

    def set_text_model(self, model_key):
        if model_key not in AVAILABLE_TEXT_MODELS:
            return {"success": False, "error": f"Unknown model: {model_key}"}
        self.config["active_text_model"] = model_key
        self.save_config()
        return {"success": True, "message": f"Switched to {AVAILABLE_TEXT_MODELS[model_key]['display_name']}"}

    def set_image_model(self, model_key):
        if model_key not in AVAILABLE_IMAGE_MODELS:
            return {"success": False, "error": f"Unknown model: {model_key}"}
        self.config["active_image_model"] = model_key
        self.save_config()
        return {"success": True, "message": f"Switched to {AVAILABLE_IMAGE_MODELS[model_key]['display_name']}"}

    def get_active_text_model_id(self):
        key = self.config.get("active_text_model", "qwen-7b")
        if key not in AVAILABLE_TEXT_MODELS:
            key = "qwen-7b"
        return AVAILABLE_TEXT_MODELS[key]["model_id"]

    def get_active_image_model_id(self):
        key = self.config.get("active_image_model", "stable-diffusion-v1-5")
        if key not in AVAILABLE_IMAGE_MODELS:
            key = "stable-diffusion-v1-5"
        return AVAILABLE_IMAGE_MODELS[key]["model_id"]

    def set_profile(self, profile_name):
        if profile_name not in DEFAULT_PROFILES:
            return {"success": False}
        self.config["active_profile"] = profile_name
        self.config["custom_params"] = {}
        self.save_config()
        return {"success": True, "params": DEFAULT_PROFILES[profile_name]}

    def set_custom_params(self, **kwargs):
        allowed = {"temperature", "max_tokens", "top_p", "repetition_penalty"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        self.config["custom_params"].update(updates)
        self.save_config()
        return {"success": True, "updated": updates}

    def get_params(self):
        return self.get_profile(self.config.get("active_profile", "balanced"))

    BLOCKED_TERMS = ["nude", "naked", "explicit", "nsfw", "violence",
                     "gore", "weapon", "illegal", "drug"]

    def filter_prompt(self, prompt):
        if not self.config.get("content_filter", True):
            return True, "Filter disabled"
        lowered = prompt.lower()
        for term in self.BLOCKED_TERMS:
            if term in lowered:
                return False, f"Prompt blocked: contains restricted content ('{term}')"
        return True, "OK"

    def get_status(self):
        text_key = self.config.get("active_text_model", "qwen-7b")
        if text_key not in AVAILABLE_TEXT_MODELS:
            text_key = "qwen-7b"
        image_key = self.config.get("active_image_model", "stable-diffusion-v1-5")
        if image_key not in AVAILABLE_IMAGE_MODELS:
            image_key = "stable-diffusion-v1-5"
        return {
            "text_model": AVAILABLE_TEXT_MODELS[text_key]["display_name"],
            "text_model_id": AVAILABLE_TEXT_MODELS[text_key]["model_id"],
            "image_model": AVAILABLE_IMAGE_MODELS[image_key]["display_name"],
            "image_model_id": AVAILABLE_IMAGE_MODELS[image_key]["model_id"],
            "profile": self.config.get("active_profile", "balanced"),
            "params": self.get_params(),
            "content_filter": self.config.get("content_filter", True),
            "generation_count": self.generation_count,
            "session_start": self.session_start,
        }

    def increment_count(self):
        self.generation_count += 1

    def get_available_models(self):
        return {
            "text_models": AVAILABLE_TEXT_MODELS,
            "image_models": AVAILABLE_IMAGE_MODELS,
            "profiles": DEFAULT_PROFILES
        }
