import json
import os
import subprocess
from PIL import Image
from utils.main import createFrame

Image.MAX_IMAGE_PIXELS = None

container_name = os.getenv("NSFW_CONTAINER", "nsfw_detect_service")
tmp_dir = os.path.abspath(os.path.join("src", "tmp"))
metadata_path = "src/detector/num_frames_per_sheet.json"

if not os.path.exists(metadata_path):
    print(f"Error: {metadata_path} not found.")
    exit(1)

with open(metadata_path, "r") as f:
    metadata = json.load(f)

nsfw_detections_by_sheet = {}

try:
    for sheet_path, num_frames in metadata.items():
        if not os.path.exists(sheet_path):
            continue

        sheet_detections = []
        print(f"Analyzing {sheet_path}...")

        with Image.open(sheet_path) as img:
            for i in range(num_frames):
                frame = createFrame(img, i)
                temp_filename = f"frame_{i}.png"
                temp_path = os.path.join(tmp_dir, temp_filename)
                frame.save(temp_path, "PNG")

                cmd = [
                    "docker", "exec", container_name,
                    "python", "classify_nsfw.py",
                    "--model_def", "nsfw_model/deploy.prototxt",
                    "--pretrained_model", "nsfw_model/resnet_50_1by2_nsfw.caffemodel",
                    f"/workspace/frames/{temp_filename}"
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                
                try:
                    output = result.stdout.strip()
                    print(f"Output for frame {i}: {output}")
                    nsfw_score = float(output.strip("()").split(", ")[1])
                except:
                    nsfw_score = -1

                sheet_detections.append( nsfw_score)
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        nsfw_detections_by_sheet[sheet_path] = sheet_detections

finally:
    output_file = "src/detector/detections.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(nsfw_detections_by_sheet, f, indent=2)