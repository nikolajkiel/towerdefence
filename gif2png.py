from PIL import Image
import numpy as np

gif = Image.open("assets/sprites/golem.gif")

# extract all frames
frames = []
for i in range(gif.n_frames):
    gif.seek(i)
    frame = gif.copy().convert("RGBA")
    # crop
    frame = frame.crop((170, 75, 450, 295))
    # frame.show()
    # break
    # replace (222,222,222) with transparent pixels
    frame = frame#.convert("RGBA")
    array = np.array(frame)
    window_size = 3
    for x in range(array.shape[0]):
        for y in range(array.shape[1]):
            win_xmin = max(0, x - window_size)
            win_xmax = min(array.shape[0], x + window_size)
            win_ymin = max(0, y - window_size)
            win_ymax = min(array.shape[1], y + window_size)
            if 222 in array[win_xmin:win_xmax, win_ymin:win_ymax, 0] and 222 in array[win_xmin:win_xmax, win_ymin:win_ymax, 1] and 222 in array[win_xmin:win_xmax, win_ymin:win_ymax, 2]:
                array[x, y, :] = [255, 255, 255, 0]
    frame = Image.fromarray(array)
    frames.append(frame)

    # save frames as png
    frame.save(f"assets/sprites/golem/golem_{i:02d}.png")



# export as gif
# remove alpha channel
frames = [frame.convert("RGB") for frame in frames]
frames[0].save('assets/sprites/golem_new.gif', append_images=frames[1:], save_all=True, duration=100, loop=0)
