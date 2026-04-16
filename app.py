import os
import gradio as gr
from model_manager import ModelManager
from text_engine import TextEngine
from image_engine import ImageEngine
from history_logger import HistoryLogger
from evaluation import Evaluator

# Check tokens
hf_token = os.environ.get("HF_TOKEN", "")
replicate_token = os.environ.get("REPLICATE_TOKEN", "")

if not hf_token:
    print("WARNING: HF_TOKEN not set! Text generation will fail.")
if not replicate_token:
    print("WARNING: REPLICATE_TOKEN not set! Image generation will fail. Get free token at replicate.com/account/api-tokens")

try:
    manager = ModelManager()
    text_engine = TextEngine(hf_token)
    image_engine = ImageEngine(replicate_token or hf_token)
    logger = HistoryLogger()
    evaluator = Evaluator()
    print("All engines initialized successfully")
except Exception as e:
    print(f"Error initializing engines: {e}")
    raise

def generate_text(prompt, model_key, profile_name, max_tokens, temperature, top_p):
    try:
        if not prompt.strip():
            return "Please enter a prompt.", "", ""
        if not hf_token:
            return "Error: HF_TOKEN not configured. Please set your Hugging Face token.", "", ""
        
        config = manager.get_model_config(model_key)
        params = manager.get_profile(profile_name)
        params.update({"max_tokens": int(max_tokens), "temperature": temperature, "top_p": top_p})
        
        text, elapsed = text_engine.generate(prompt, config["model_id"], **params)
        
        if text.startswith("Error:"):
            return text, "", ""
        
        bleu = evaluator.bleu_score(prompt, text)
        logger.log("text", prompt, text, model_key, params, {"bleu": bleu, "time": elapsed})
        return text, f"BLEU: {bleu:.4f} | Time: {elapsed:.2f}s", ""
    except Exception as e:
        print(f"Text generation error: {e}")
        return f"Error: {str(e)}", "", ""

def generate_image(prompt, model_key, width, height, steps):
    try:
        if not prompt.strip():
            return None, "Please enter a prompt."
        if not replicate_token and not hf_token:
            return None, "Error: REPLICATE_TOKEN not configured. Get free token at replicate.com/account/api-tokens"
        
        config = manager.get_image_model_config(model_key)
        image_url, elapsed, message = image_engine.generate(
            prompt, config["model_id"], int(width), int(height), int(steps)
        )
        
        if image_url:
            logger.log("image", prompt, image_url, model_key, {}, {"time": elapsed})
            # Return the URL as a string - Gradio will display it as image
            return image_url, f"Generated in {elapsed:.2f}s - Click to view full size"
        else:
            error_msg = f"Failed: {message}. Time: {elapsed:.2f}s"
            print(error_msg)
            return None, error_msg
            
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Image generation error: {error_msg}")
        return None, error_msg

def generate_both(prompt, text_model, image_model, profile, max_tokens, temperature, top_p, width, height, steps):
    try:
        text_out, text_meta, _ = generate_text(prompt, text_model, profile, max_tokens, temperature, top_p)
        image_out, image_meta = generate_image(prompt, image_model, width, height, steps)
        return text_out, text_meta, image_out, image_meta
    except Exception as e:
        print(f"Generate both error: {e}")
        return f"Error: {str(e)}", "", None, ""

def get_history():
    try:
        entries = logger.get_history(20)
        if not entries:
            return "No history yet."
        lines = []
        for e in reversed(entries):
            lines.append(f"**{e['type'].upper()}** [{e['model']}] {e['timestamp'][:19]}\n> {e['prompt'][:80]}...")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error loading history: {e}"

def export_history():
    try:
        path = logger.export_csv()
        return path
    except Exception as e:
        return f"Error: {e}"

def rate_last(rating):
    try:
        logger.rate_last(int(rating))
        return f"Rated {rating}/5 ✓"
    except Exception as e:
        return f"Error: {e}"

# Get model lists safely
try:
    text_models = manager.get_text_model_keys()
    image_models = manager.get_image_model_keys()
    profiles = manager.get_profile_names()
    print(f"Available models: text={text_models}, image={image_models}, profiles={profiles}")
except Exception as e:
    print(f"Error getting model lists: {e}")
    text_models = ["qwen-7b", "llama-8b", "deepseek"]
    image_models = ["stable-diffusion-v1-5", "sdxl-base"]
    profiles = ["balanced", "creative", "precise", "fast"]

with gr.Blocks(title="AICIG - AI Content & Image Generator", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 AICIG — AI Content & Image Generator\n**Final Year Project** | Local LLM + Image Generation System")

    with gr.Tabs():
        with gr.Tab("📝 Text Generation"):
            with gr.Row():
                with gr.Column(scale=2):
                    t_prompt = gr.Textbox(label="Prompt", placeholder="Write a blog post about...", lines=4)
                    with gr.Row():
                        t_model = gr.Dropdown(choices=text_models, value=text_models[0] if text_models else "qwen-7b", label="Model")
                        t_profile = gr.Dropdown(choices=profiles, value=profiles[0] if profiles else "balanced", label="Profile")
                    with gr.Row():
                        t_tokens = gr.Slider(50, 500, value=300, step=10, label="Max Tokens")
                        t_temp = gr.Slider(0.1, 2.0, value=0.7, step=0.1, label="Temperature")
                        t_top_p = gr.Slider(0.1, 1.0, value=0.9, step=0.1, label="Top-P")
                    t_btn = gr.Button("Generate Text", variant="primary")
                with gr.Column(scale=3):
                    t_out = gr.Textbox(label="Generated Text", lines=12)
                    t_meta = gr.Textbox(label="Metrics", interactive=False)
                    with gr.Row():
                        t_rating = gr.Slider(1, 5, value=3, step=1, label="Rate this output")
                        t_rate_btn = gr.Button("Submit Rating")
                    t_rate_out = gr.Textbox(label="", interactive=False)
            t_btn.click(generate_text, [t_prompt, t_model, t_profile, t_tokens, t_temp, t_top_p], [t_out, t_meta, t_rate_out])
            t_rate_btn.click(rate_last, [t_rating], [t_rate_out])

        with gr.Tab("🖼️ Image Generation"):
            with gr.Row():
                with gr.Column(scale=2):
                    i_prompt = gr.Textbox(label="Image Prompt", placeholder="A futuristic city at sunset...", lines=4)
                    i_model = gr.Dropdown(choices=image_models, value=image_models[0] if image_models else "stable-diffusion-v1-5", label="Image Model")
                    with gr.Row():
                        i_width = gr.Slider(256, 1024, value=512, step=64, label="Width")
                        i_height = gr.Slider(256, 1024, value=512, step=64, label="Height")
                        i_steps = gr.Slider(10, 50, value=20, step=5, label="Steps")
                    i_btn = gr.Button("Generate Image", variant="primary")
                with gr.Column(scale=3):
                    # Use HTML component to display image from URL
                    i_out = gr.Image(label="Generated Image", type="filepath")
                    i_meta = gr.Textbox(label="Info", interactive=False)
            i_btn.click(generate_image, [i_prompt, i_model, i_width, i_height, i_steps], [i_out, i_meta])

        with gr.Tab("🔀 Generate Both"):
            b_top_p_state = gr.State(0.9)
            with gr.Row():
                with gr.Column(scale=2):
                    b_prompt = gr.Textbox(label="Prompt", placeholder="Describe something to write about AND generate an image of...", lines=4)
                    with gr.Row():
                        b_tmodel = gr.Dropdown(choices=text_models, value=text_models[0] if text_models else "qwen-7b", label="Text Model")
                        b_imodel = gr.Dropdown(choices=image_models, value=image_models[0] if image_models else "stable-diffusion-v1-5", label="Image Model")
                    b_profile = gr.Dropdown(choices=profiles, value=profiles[0] if profiles else "balanced", label="Profile")
                    with gr.Row():
                        b_tokens = gr.Slider(50, 500, value=300, step=10, label="Max Tokens")
                        b_temp = gr.Slider(0.1, 2.0, value=0.7, step=0.1, label="Temperature")
                    with gr.Row():
                        b_width = gr.Slider(256, 1024, value=512, step=64, label="Width")
                        b_height = gr.Slider(256, 1024, value=512, step=64, label="Height")
                        b_steps = gr.Slider(10, 50, value=20, step=5, label="Steps")
                    b_btn = gr.Button("Generate Both", variant="primary", size="lg")
                with gr.Column(scale=3):
                    b_tout = gr.Textbox(label="Generated Text", lines=8)
                    b_tmeta = gr.Textbox(label="Text Metrics", interactive=False)
                    b_iout = gr.Image(label="Generated Image", type="filepath")
                    b_imeta = gr.Textbox(label="Image Info", interactive=False)
            b_btn.click(generate_both,
                inputs=[b_prompt, b_tmodel, b_imodel, b_profile, b_tokens, b_temp, b_top_p_state, b_width, b_height, b_steps],
                outputs=[b_tout, b_tmeta, b_iout, b_imeta])

        with gr.Tab("🗂️ Model Manager"):
            gr.Markdown("### Available Models & Configurations")
            def show_config():
                try:
                    cfg = manager.get_full_config()
                    lines = ["**Text Models:**"]
                    for k, v in cfg["text_models"].items():
                        lines.append(f"- `{k}`: {v['name']} — {v['description']}")
                    lines.append("\n**Image Models:**")
                    for k, v in cfg["image_models"].items():
                        lines.append(f"- `{k}`: {v['name']} — {v['description']}")
                    lines.append("\n**Profiles:**")
                    for k, v in cfg["profiles"].items():
                        lines.append(f"- `{k}`: temp={v.get('temperature', '?')}, top_p={v.get('top_p', '?')}")
                    return "\n".join(lines)
                except Exception as e:
                    return f"Error loading config: {e}"
            cfg_out = gr.Markdown()
            gr.Button("Load Config").click(show_config, [], [cfg_out])

        with gr.Tab("📊 History & Export"):
            gr.Markdown("### Generation History")
            hist_out = gr.Markdown()
            with gr.Row():
                gr.Button("Refresh History").click(get_history, [], [hist_out])
                export_btn = gr.Button("Export CSV")
            export_file = gr.File(label="Download CSV")
            export_btn.click(export_history, [], [export_file])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(
        server_name="0.0.0.0", 
        server_port=port,
        share=False,
        show_api=False,
        inbrowser=False,
        prevent_thread_lock=True
    )
