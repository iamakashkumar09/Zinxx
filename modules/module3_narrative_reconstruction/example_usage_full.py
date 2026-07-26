import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from modules import module1_dream_understanding as module1
from modules.module2_dream_graph import build_and_persist_graph, init_db
from modules.module3_narrative_reconstruction import (
    NarrativeReconstructionEngine,
    SessionMeta,
    ReconstructionConfig,
)


async def main():
    print("=== Dream to Story Pipeline Test (Modules 1 -> 2 -> 3) ===\n")
    
    # Check if necessary keys are present
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("GROQ_API_KEY"):
        print("[WARNING] OPENAI_API_KEY or GROQ_API_KEY not found in environment.")
        print("Please configure your .env file to see real LLM results.\n")
        
    dream_text = "I was in a dark forest running away from a shadow that looked like a wolf, but when I turned around it was a little girl holding a red balloon."
    user_id = "user_demo_full"
    dream_id = "dream_demo_full_1"
    session_id = "sess_demo_full_1"
    
    print("--- Step 1: Module 1 (Story Extraction) ---")
    print(f"Input text: '{dream_text}'")
    try:
        story = module1.process(dream_text)
        print(f"✅ Extracted {len(story.characters)} characters and {len(story.scenes)} scenes.")
        for char in story.characters:
            print(f"   - Character: {char.name} ({char.role})")
    except Exception as e:
        print(f"❌ Module 1 failed: {e}")
        return

    print("\n--- Step 2: Module 2 (Dream Graph Build) ---")
    print("Initializing Database...")
    try:
        await init_db()
        graph = await build_and_persist_graph(
            dream_id=dream_id,
            user_id=user_id,
            story=story
        )
        print(f"✅ Graph built with {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
        totems = [n for n in graph.nodes if getattr(n, "is_recurring_symbol", False)]
        if totems:
            print(f"   - Detected recurring symbols: {[t.label for t in totems]}")
    except ConnectionRefusedError:
        print("❌ Module 2 failed: Connection refused.")
        print("Note: Module 2 requires Postgres with pgvector installed and running.")
        print("Please check DREAM_DB_URL in your .env file.")
        return
    except Exception as e:
        print(f"❌ Module 2 failed: {e}")
        print("Note: Module 2 requires Postgres with pgvector installed.")
        return

    print("\n--- Step 3: Module 3 (Narrative Reconstruction) ---")
    try:
        session = SessionMeta(dream_id=dream_id, user_id=user_id, session_id=session_id)
        config = ReconstructionConfig(model_tier="draft", preserve_dream_logic=True, debug=False)
        
        request = NarrativeReconstructionEngine.input_from_graph(
            graph=graph,
            session_meta=session,
            config=config,
        )
        
        # Instantiate engine. If OPENAI_API_KEY is not set, it defaults to mock_mode=True
        engine = NarrativeReconstructionEngine()
        output = engine.reconstruct(request)
        
        print(f"✅ Narrative Output ID: {output.narrative_id}")
        print(f"   Generated {len(output.beats)} narrative beats:\n")
        
        for beat in output.beats:
            print(f"  [{beat.order}] Tone: {beat.emotional_tone}")
            print(f"        Text: {beat.narrative_text}")
            for gf in beat.gap_fills:
                print(f"        * Gap-fill (conf={gf.confidence}): {gf.fill_content}")
            print()
            
    except Exception as e:
        print(f"❌ Module 3 failed: {e}")
        return
        
    print("\n--- Pipeline Completed Successfully ---")


if __name__ == "__main__":
    asyncio.run(main())
