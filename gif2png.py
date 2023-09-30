from PIL import Image
import numpy as np
from pathlib import Path
from sheet2pngs import strip_frame, make_transparent

def gif_splitter(gif_path, crop_window=(170, 75, 450, 295), transparent_color=None):
    path = Path(gif_path)
    gif = Image.open(path)

    # extract all frames
    frames = []
    for i in range(gif.n_frames):
        gif.seek(i)
        frame = gif.copy().convert("RGBA")
        # crop
        if crop_window:
            frame = frame.crop(crop_window)
        # frame.show()
        # break
        # replace (222,222,222) with transparent pixels
        frame = make_transparent(frame)
        frames.append(frame)
        
        frame_red = strip_frame(frame)
        # save frames as png
        frame_path = path.parent / f"{path.parent.stem}_{i:02d}.png"
        frame_red.save(frame_path)




    # export as gif
    # remove alpha channel
    frames = [frame.convert("RGB") for frame in frames]
    frames[0].save(path.parent / (path.parent.stem + '_new.gif'), append_images=frames[1:], save_all=True, duration=100, loop=0)


if __name__ == "__main__":
    gif_path = 'assets/sprites/golem/golem.gif'
    gif_splitter(gif_path)