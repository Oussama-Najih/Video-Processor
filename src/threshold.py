import os
import json

THRESHOLD = 0.6

DETECTIONS_INPUT = "src/detector/detections.json"
METADATA_OUTPUT = os.path.join("src", "highscore", "high_score_frames.json")

os.makedirs(os.path.dirname(METADATA_OUTPUT), exist_ok=True)

if not os.path.exists(DETECTIONS_INPUT):
    print(f"Error: {DETECTIONS_INPUT} not found.")
    exit(1)

with open(DETECTIONS_INPUT, "r") as f:
    detections = json.load(f)

high_score_results = []

for item in detections:
    if item["score"] >= THRESHOLD:
        high_score_results.append({
            "timestamp": item["time"],
            "score": round(item["score"], 4)
        })

high_score_results.sort(key=lambda x: x["timestamp"])

with open(METADATA_OUTPUT, "w") as f:
    json.dump(high_score_results, f, indent=2)

print(f"Filtered {len(high_score_results)} high-score frames.")
print(f"Results saved to {METADATA_OUTPUT}")