import asyncio
import os
import sys
from dotenv import load_dotenv

# Force UTF-8 for console prints
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

from modules import module1_dream_understanding as module1
from modules.module2_dream_graph import build_and_persist_graph, init_db
from modules.module3_narrative_reconstruction import (
    NarrativeReconstructionEngine,
    SessionMeta,
    ReconstructionConfig,
)
from modules.module7_screenplay_conversion.converter import convert_to_screenplay
from modules import module8_audio_direction as module8
from modules import module9_audio_production as module9
from modules import module10_mixing_timeline as module10
from shared.config import OUTPUT_DIR
async def main():
    print("=== Pipeline Test (Modules 1 -> 2 -> 3 -> 7) ===\n")
    
    dream_text = "I was in a dark forest running away from a shadow that looked like a wolf, but when I turned around it was a little girl holding a red balloon."
    user_id = "user_demo_pipeline"
    
    import uuid
    dream_id = f"dream_{uuid.uuid4().hex[:8]}"
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    
    print("--- Step 1: Module 1 (Story Extraction) ---")
    story = module1.process(dream_text)
    print(f"Extracted {len(story.characters)} characters and {len(story.scenes)} scenes.")
    
    print("\n--- Step 2: Module 2 (Dream Graph Build) ---")
    await init_db()
    graph = await build_and_persist_graph(dream_id=dream_id, user_id=user_id, story=story)
    print(f"Graph built with {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
    
    print("\n--- Step 3: Module 3 (Narrative Reconstruction) ---")
    session = SessionMeta(dream_id=dream_id, user_id=user_id, session_id=session_id)
    config = ReconstructionConfig(model_tier="draft", preserve_dream_logic=True, debug=False)
    request = NarrativeReconstructionEngine.input_from_graph(graph=graph, session_meta=session, config=config)
    
    engine3 = NarrativeReconstructionEngine()
    output3 = engine3.reconstruct(request)
    print(f"Generated {len(output3.beats)} narrative beats.")
    
    print("\n--- Step 4: Module 7 (Screenplay Conversion) ---")
    story_converted = convert_to_screenplay(narrative=output3, graph=graph)
    print(f"Screenplay Title: {story_converted.title}")
    print(f"Screenplay Scenes generated: {len(story_converted.scenes)}")
    for s in story_converted.scenes:
        print(f"  Scene: {s.setting}")
        print(f"    - Lines: {len(s.lines)}")
        print(f"    - SFX Cues: {len(s.sound_cues)}")

    print("\n--- Step 5: Module 8 (Audio Direction) ---")
    story_converted = module8.process(story_converted)
    print("Added performance directions and emotion scores to lines.")

    print("\n--- Step 6: Module 9 (Audio Production) ---")
    import uuid
    from pathlib import Path
    import shutil
    
    tmp_dir = OUTPUT_DIR / "tmp" / uuid.uuid4().hex
    try:
        story_converted = module9.process(story_converted, tmp_dir)
        print("Generated voices and sound effects successfully.")
        
        print("\n--- Step 7: Module 10 (Mixing Timeline) ---")
        final_path = module10.process(story_converted, OUTPUT_DIR)
        print(f"Mixed final audio successfully: {final_path}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n=== All modules passed! ===")

if __name__ == "__main__":
    asyncio.run(main())
