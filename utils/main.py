import os
import shutil


COLS = 10
FRAME_W = 320
FRAME_H = 180

def createFrame(img,i):
    row = i // COLS
    col = i % COLS

    left = col * FRAME_W
    upper = row * FRAME_H
    right = left + FRAME_W
    lower = upper + FRAME_H

    sprite_w, sprite_h = img.size
    if right > sprite_w or lower > sprite_h:
        return False

    frame = img.crop((left, upper, right, lower))
    frame = frame.convert("RGB")
    return frame


def delete_tmp_content():
    folder = 'src/tmp'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')