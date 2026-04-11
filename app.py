"""
AICIG Final System - Gradio Interface
Shefat Mazibar (W1967304) | Supervisor: Jeffrey Ferguson
University of Westminster
"""

import os
import gradio as gr
from model_manager import ModelManager, AVAILABLE_TEXT_MODELS, AVAILABLE_IMAGE_MODELS, DEFAULT_PROFILES
from text_engine import TextEngine
from image_engine import ImageEngine
from history_logger import HistoryLogger
from evaluation import Evaluator

HF_TOKEN = os.environ.get("HF_TOKEN", "")
manager = ModelManager()
text_engine = TextEngine(HF_TOKEN)
image_engine = ImageEngine(HF_TOKEN)
logger = HistoryLogger()
evaluator = Evaluator()

TEXT_MODEL_CHOICES = [(v["display_name"], k) for k, v in AVAILABLE_TEXT_MODELS.items()]
IMAGE_MODEL_CHOICES = [(v["display_name"], k) for k, v in AVAILABLE_IMAGE_MODELS.items()]
PROFILE_CHOICES = list(DEFAULT_PROFILES.keys())
DEFAULT_TEXT_MODEL = list(AVAILABLE_TEXT_MODELS.keys())[0]
DEFAULT_IMAGE_MODEL = list(AVAILABLE_IMAGE_MODELS.keys())[0]


def generate_text(prompt, text_model_key, profile, temp, max_tok, top_p, rep_pen):
    if not prompt.strip():
        return "Please enter a prompt.", "", ""
    safe, msg = manager.filter_prompt(prompt)
    if not safe:
        return f"Blocked: {msg}", "", ""
    manager.set_text_model(text_model_key)
    manager.set_profile(profile)
    manager.set_custom_params(temperature=float(temp), max_tokens=int(max_tok),
                               top_p=float(top_p), repetition_penalty=float(rep_pen))
    model_id = manager.get_active_text_model_id()
    params = manager.get_params()
    text, duration = text_engine.generate(
        prompt=prompt, model_id=model_id,
        max_tokens=int(params["max_tokens"]),
        temperature=float(params["temperature"]),
        top_p=float(params["top_p"]),
        repetition_penalty=float(params["repetition_penalty"]),
    )
    report = evaluator.evaluate(text, prompt)
    eval_str = evaluator.format_report(report)
    entry_id = logger.log(
        prompt=prompt, generation_type="text", text_output=text,
        image_generated=False,
        text_model=AVAILABLE_TEXT_MODELS[text_model_key]["display_name"],
        image_model="N/A", params=params, duration_seconds=duration,
        bleu_score=report.get("bleu_score"),
    )
    manager.increment_count()
    return text, eval_str, f"Done in {duration:.1f}s | ID: {entry_id}"


def generate_image(prompt, image_model_key, profile, steps, guidance):
    if not prompt.strip():
        return None, "Please enter a prompt.", ""
    safe, msg = manager.filter_prompt(prompt)
    if not safe:
        return None, f"Blocked: {msg}", ""
    manager.set_image_model(image_model_key)
    manager.set_profile(profile)
    manager.set_custom_params(image_steps=int(steps), image_guidance=float(guidance))
    model_id = manager.get_active_image_model_id()
    params = manager.get_params()
    img, duration = image_engine.generate(
        prompt=prompt, model_id=model_id,
        num_inference_steps=int(params["image_steps"]),
        guidance_scale=float(params["image_guidance"]),
    )
    if img is None:
        return None, "Image generation failed — model may be loading. Retry in 20s.", ""
    entry_id = logger.log(
        prompt=prompt, generation_type="image", text_output=None,
        image_generated=True, text_model="N/A",
        image_model=AVAILABLE_IMAGE_MODELS[image_model_key]["display_name"],
        params=params, duration_seconds=duration,
    )
    manager.increment_count()
    return img, f"Done in {duration:.1f}s | ID: {entry_id}", entry_id


def generate_combined(prompt, text_model_key, image_model_key, profile,
                      temp, max_tok, top_p, rep_pen, steps, guidance):
    if not prompt.strip():
        return "Please enter a prompt.", None, "", ""
    safe, msg = manager.filter_prompt(prompt)
    if not safe:
        return f"Blocked: {msg}", None, "", ""
    manager.set_text_model(text_model_key)
    manager.set_image_model(image_model_key)
    manager.set_profile(profile)
    manager.set_custom_params(
        temperature=float(temp), max_tokens=int(max_tok),
        top_p=float(top_p), repetition_penalty=float(rep_pen),
        image_steps=int(steps), image_guidance=float(guidance)
    )
    params = manager.get_params()
    text, t_dur = text_engine.generate(
        prompt=prompt, model_id=manager.get_active_text_model_id(),
        max_tokens=int(params["max_tokens"]),
        temperature=float(params["temperature"]),
        top_p=float(params["top_p"]),
        repetition_penalty=float(params["repetition_penalty"]),
    )
    img, i_dur = image_engine.generate(
        prompt=prompt, model_id=manager.get_active_image_model_id(),
        num_inference_steps=int(params["image_steps"]),
        guidance_scale=float(params["image_guidance"]),
    )
    report = evaluator.evaluate(text, prompt)
    eval_str = evaluator.format_report(report)
    entry_id = logger.log(
        prompt=prompt, generation_type="combined", text_output=text,
        image_generated=img is not None,
        text_model=AVAILABLE_TEXT_MODELS[text_model_key]["display_name"],
        image_model=AVAILABLE_IMAGE_MODELS[image_model_key]["display_name"],
        params=params, duration_seconds=t_dur + i_dur,
        bleu_score=report.get("bleu_score"),
    )
    manager.increment_count()
    return text, img, eval_str, f"Text: {t_dur:.1f}s | Image: {i_dur:.1f}s | ID: {entry_id}"


def submit_rating(entry_id, rating, feedback):
    if not entry_id:
        return "No entry ID provided."
    success = logger.rate(entry_id.strip(), int(rating), feedback)
    return f"Rating saved for {entry_id}" if success else f"Entry not found: {entry_id}"


def get_history():
    recent = logger.get_recent(10)
    if not recent:
        return "No generations yet."
    lines = []
    for e in recent:
        lines.append(f"**{e['id']}** | {e['type']} | {e['timestamp'][:16]} | Rating: {e.get('user_rating') or 'unrated'}\n> {e['prompt'][:80]}")
    return "\n\n".join(lines)


def get_stats():
    stats = logger.get_stats()
    status = manager.get_status()
    return "\n".join([
        "## System Stats",
        f"- Total generations: **{stats.get('total', 0)}**",
        f"- Rated: **{stats.get('rated_count', 0)}**",
        f"- Average rating: **{stats.get('average_rating') or 'N/A'}**",
        f"- Avg generation time: **{stats.get('avg_duration_seconds') or 'N/A'}s**",
        "",
        "## Current Config",
        f"- Text model: **{status['text_model']}**",
        f"- Image model: **{status['image_model']}**",
        f"- Profile: **{status['profile']}**",
        f"- Session generations: **{status['generation_count']}**",
    ])


def export_csv():
    return logger.export_csv()


with gr.Blocks(title="AICIG", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AICIG — AI Content & Image Generator\n**Final Year Project** | Shefat Mazibar (W1967304) | University of Westminster")

    with gr.Tabs():
        with gr.Tab("Combined Generation"):
            gr.Markdown("Generate both text and image from a single prompt.")
            with gr.Row():
                with gr.Column():
                    c_prompt = gr.Textbox(label="Prompt", lines=3, placeholder="A futuristic city at night...")
                    with gr.Row():
                        c_text_model = gr.Dropdown(TEXT_MODEL_CHOICES, value=DEFAULT_TEXT_MODEL, label="Text Model")
                        c_img_model = gr.Dropdown(IMAGE_MODEL_CHOICES, value=DEFAULT_IMAGE_MODEL, label="Image Model")
                    c_profile = gr.Dropdown(PROFILE_CHOICES, value="balanced", label="Parameter Profile")
                    with gr.Accordion("Advanced Parameters", open=False):
                        c_temp = gr.Slider(0.1, 1.5, value=0.7, step=0.05, label="Temperature")
                        c_maxtok = gr.Slider(50, 500, value=300, step=25, label="Max Tokens")
                        c_topp = gr.Slider(0.5, 1.0, value=0.9, step=0.05, label="Top-p")
                        c_repen = gr.Slider(1.0, 1.5, value=1.1, step=0.05, label="Repetition Penalty")
                        c_steps = gr.Slider(10, 50, value=25, step=5, label="Image Steps")
                        c_guidance = gr.Slider(1.0, 15.0, value=7.5, step=0.5, label="Guidance Scale")
                    c_btn = gr.Button("Generate Both", variant="primary")
                with gr.Column():
                    c_text_out = gr.Textbox(label="Generated Text", lines=8, show_copy_button=True)
                    c_img_out = gr.Image(label="Generated Image", height=350)
                    c_eval_out = gr.Markdown()
                    c_status = gr.Markdown()
            c_btn.click(generate_combined,
                inputs=[c_prompt, c_text_model, c_img_model, c_profile, c_temp, c_maxtok, c_topp, c_repen, c_steps, c_guidance],
                outputs=[c_text_out, c_img_out, c_eval_out, c_status])
            gr.Examples([
                ["A serene Japanese garden with cherry blossoms at dawn"],
                ["A futuristic robot teacher in a holographic classroom"],
                ["An astronaut exploring ancient ruins on Mars"],
            ], inputs=c_prompt)

        with gr.Tab("Text Generation"):
            gr.Markdown("Generate text using instruction-tuned LLMs.")
            with gr.Row():
                with gr.Column():
                    t_prompt = gr.Textbox(label="Prompt", lines=4, placeholder="Write a short article about AI...")
                    t_model = gr.Dropdown(TEXT_MODEL_CHOICES, value=DEFAULT_TEXT_MODEL, label="Text Model")
                    t_profile = gr.Dropdown(PROFILE_CHOICES, value="balanced", label="Profile")
                    with gr.Accordion("Parameters", open=False):
                        t_temp = gr.Slider(0.1, 1.5, value=0.7, step=0.05, label="Temperature")
                        t_maxtok = gr.Slider(50, 500, value=300, step=25, label="Max Tokens")
                        t_topp = gr.Slider(0.5, 1.0, value=0.9, step=0.05, label="Top-p")
                        t_repen = gr.Slider(1.0, 1.5, value=1.1, step=0.05, label="Repetition Penalty")
                    t_btn = gr.Button("Generate Text", variant="primary")
                with gr.Column():
                    t_out = gr.Textbox(label="Output", lines=15, show_copy_button=True)
                    t_eval = gr.Markdown()
                    t_status = gr.Markdown()
            t_btn.click(generate_text,
                inputs=[t_prompt, t_model, t_profile, t_temp, t_maxtok, t_topp, t_repen],
                outputs=[t_out, t_eval, t_status])

        with gr.Tab("Image Generation"):
            gr.Markdown("Generate images from text prompts.")
            with gr.Row():
                with gr.Column():
                    i_prompt = gr.Textbox(label="Prompt", lines=3, placeholder="A magical forest...")
                    i_model = gr.Dropdown(IMAGE_MODEL_CHOICES, value=DEFAULT_IMAGE_MODEL, label="Image Model")
                    i_profile = gr.Dropdown(PROFILE_CHOICES, value="balanced", label="Profile")
                    with gr.Accordion("Parameters", open=False):
                        i_steps = gr.Slider(10, 50, value=25, step=5, label="Inference Steps")
                        i_guidance = gr.Slider(1.0, 15.0, value=7.5, step=0.5, label="Guidance Scale")
                    i_btn = gr.Button("Generate Image", variant="primary")
                    i_entry_id = gr.Textbox(label="Entry ID", visible=False)
                with gr.Column():
                    i_out = gr.Image(label="Generated Image", height=450)
                    i_status = gr.Markdown()
            i_btn.click(generate_image,
                inputs=[i_prompt, i_model, i_profile, i_steps, i_guidance],
                outputs=[i_out, i_status, i_entry_id])

        with gr.Tab("Evaluation & Rating"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Rate a Generation")
                    r_id = gr.Textbox(label="Entry ID")
                    r_rating = gr.Slider(1, 5, value=3, step=1, label="Rating (1-5)")
                    r_feedback = gr.Textbox(label="Feedback (optional)", lines=2)
                    r_btn = gr.Button("Submit Rating", variant="primary")
                    r_status = gr.Markdown()
                    r_btn.click(submit_rating, inputs=[r_id, r_rating, r_feedback], outputs=r_status)
                with gr.Column():
                    gr.Markdown("### Recent History")
                    hist_out = gr.Markdown()
                    hist_btn = gr.Button("Refresh History")
                    hist_btn.click(get_history, outputs=hist_out)
            stats_out = gr.Markdown()
            stats_btn = gr.Button("View Stats")
            stats_btn.click(get_stats, outputs=stats_out)
            export_out = gr.Textbox(label="CSV Export", lines=5, show_copy_button=True)
            export_btn = gr.Button("Export CSV")
            export_btn.click(export_csv, outputs=export_out)

        with gr.Tab("Model Manager"):
            gr.Markdown("### Model & Parameter Management")
            with gr.Row():
                with gr.Column():
                    cfg_out = gr.Markdown()
                    cfg_btn = gr.Button("Refresh Status")
                    cfg_btn.click(get_stats, outputs=cfg_out)
                with gr.Column():
                    gr.Markdown("**Text Models:**")
                    for k, v in AVAILABLE_TEXT_MODELS.items():
                        gr.Markdown(f"- **{v['display_name']}**: {v['description']}")
                    gr.Markdown("**Image Models:**")
                    for k, v in AVAILABLE_IMAGE_MODELS.items():
                        gr.Markdown(f"- **{v['display_name']}**: {v['description']}")
            gr.Markdown("**Parameter Profiles:**")
            for name, p in DEFAULT_PROFILES.items():
                gr.Markdown(f"- **{name}**: {p['description']} (temp={p['temperature']}, steps={p['image_steps']})")

    gr.Markdown("---\n**AICIG** | Shefat Mazibar (W1967304) | Jeffrey Ferguson | University of Westminster")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
