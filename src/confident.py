import os
import json


THRESHOLD = 0.7
FRAME_INTERVAL = 2  

DETECTIONS_INPUT = "src/detector/detections.json"
METADATA_OUTPUT = os.path.join("src", "highscore", "high_score_frames.json")

os.makedirs(os.path.dirname(METADATA_OUTPUT), exist_ok=True)


if not os.path.exists(DETECTIONS_INPUT):
    print(f"Error: {DETECTIONS_INPUT} not found.")
    exit(1)

with open(DETECTIONS_INPUT, "r") as f:
    nsfw_detections_by_sheet = json.load(f)


high_score_results = []

current_time_offset = 0

for sheet_path, scores in nsfw_detections_by_sheet.items():
    for index, score in enumerate(scores):
        if score >= THRESHOLD:
            timestamp = current_time_offset + (index * FRAME_INTERVAL)
            
            result = {
                "timestamp": timestamp,
                "score": round(score, 4)
            }
            high_score_results.append(result)
    
    current_time_offset += len(scores) * FRAME_INTERVAL

high_score_results.sort(key=lambda x: x["timestamp"])


with open(METADATA_OUTPUT, "w") as f:
    json.dump(high_score_results, f, indent=2)

print(f"Filtered {len(high_score_results)} high-score frames.")
print(f"Results saved to {METADATA_OUTPUT}")