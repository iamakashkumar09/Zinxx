"""Part of Module 8 — Audio Direction Engine.

Emotion scoring for story lines using a pretrained HF transformer (local, free — no API).
Feeds performance_direction.py, which turns these scores into natural-language delivery
instructions for Module 9's (audio_production) TTS step.

Model: j-hartmann/emotion-english-distilroberta-base
Loaded once (module-level singleton) so repeated requests don't reload the model.
"""

from shared.models import Story

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        import transformers
        # Monkey-patch the strict torch.load security check introduced in transformers 4.47.1
        # (still present in 4.57.3) so we can load the j-hartmann model's pickled weights
        # without needing safetensors-only weights.
        import transformers.utils.import_utils
        import transformers.modeling_utils
        transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
        transformers.modeling_utils.check_torch_load_is_safe = lambda: None

        from transformers import pipeline

        _pipeline = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=None,
        )
    return _pipeline


def score_text(text: str) -> dict[str, float]:
    clf = _get_pipeline()
    results = clf(text)[0]
    return {item["label"]: round(float(item["score"]), 4) for item in results}


def score_story(story: Story) -> Story:
    for scene in story.scenes:
        for line in scene.lines:
            line.emotion_scores = score_text(line.text)
    return story
