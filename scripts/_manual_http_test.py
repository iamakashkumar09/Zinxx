import json
import time
import urllib.request

BASE = "http://127.0.0.1:8130"

text = (
    "I was in my grandfather's attic on a golden afternoon, dust floating in the sunbeams, "
    "completely at peace, running my hand along old boxes I hadn't seen in years. Then I "
    "noticed the sky outside the small window had gone grey, and wind started rattling the "
    "glass. The floorboards behind me creaked even though I was alone, and a cold fear crept "
    "up my spine as a shadow stretched across the top of the stairs, growing closer with "
    "every heartbeat. Suddenly the fear turned to fury -- I spun around and screamed at the "
    "shadow to leave, thunder cracking outside as if answering me, refusing to back down "
    "even as it loomed over me. Then, just as suddenly, the storm broke. Sunlight poured "
    "back through the window, the shadow was gone, and I stood there laughing with relief, "
    "the warm afternoon light settling over everything again like nothing had happened."
)

story_req = json.dumps({"text": text}).encode()
req = urllib.request.Request(f"{BASE}/api/story", data=story_req, headers={"Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req, timeout=60) as resp:
    story = json.loads(resp.read())
print(f"STORY OK ({time.time()-t0:.1f}s): {story['title']}")
for s in story["scenes"]:
    speakers = sorted({l["speaker"] for l in s["lines"]})
    print(f"  scene {s['id']} [{s['emotional_tone']}] speakers={speakers}")

audio_req = json.dumps({"story": story}).encode()
req2 = urllib.request.Request(f"{BASE}/api/audio", data=audio_req, headers={"Content-Type": "application/json"})
t0 = time.time()
with urllib.request.urlopen(req2, timeout=120) as resp2:
    result = json.loads(resp2.read())
print(f"AUDIO OK ({time.time()-t0:.1f}s): {result['audio_url']}")
print("AUDIO_FILENAME:" + result["audio_url"].split("/")[-1])
