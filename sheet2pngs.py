from PIL import Image
from PIL import ImageDraw
import numpy as np
from pathlib import Path

def measuring_tape(image, major_marker=500, minor_marker=100, color=((255,0,0), (255,127,127))):
    '''
    Add minor and major marker along the edges of the image
    '''
    draw = ImageDraw.Draw(image)
    # add major markers
    for x in range(0, image.width, major_marker):
        draw.line((x, 0, x, image.height), fill=color[0], width=5)
    for y in range(0, image.height, major_marker):
        draw.line((0, y, image.width, y), fill=color[0], width=5)
    # add minor markers
    for x in range(0, image.width, minor_marker):
        draw.line((x, 0, x, image.height), fill=color[1], width=2)
    for y in range(0, image.height, minor_marker):
        draw.line((0, y, image.width, y), fill=color[1], width=2)
    return image

def make_transparent(frame, transparent_color=(222,222,222), window_size=2):
    '''
    replace transparent_color with transparent pixels

    Parameters:
    -----------
    frame: PIL.Image
        image to be processed (RGBA)
    
    transparent_color: tuple
        color to be replaced with transparent pixels
    
    window_size: int
        size of window to search for transparent_color
    '''
    assert frame.mode == 'RGBA', "frame must be RGBA"
    array = np.array(frame)
    window_size = 2
    for y in range(array.shape[0]):
        for x in range(array.shape[1]):
            win_xmin = max(0, x - window_size)
            win_xmax = min(array.shape[1], x + window_size)
            win_ymin = max(0, y - window_size)
            win_ymax = min(array.shape[0], y + window_size)
            R = array[win_ymin:win_ymax, win_xmin:win_xmax, 0]
            G = array[win_ymin:win_ymax, win_xmin:win_xmax, 1]
            B = array[win_ymin:win_ymax, win_xmin:win_xmax, 2]
            if transparent_color[0] in R and transparent_color[1] in G and transparent_color[2] in B:
                array[y, x, :] = [255, 255, (transparent_color[2]+1)%255, 0]
            else:
                pass
    return Image.fromarray(array)

def strip_frame(frame):
    '''
    remove transparent pixels from frame

    Parameters:
    -----------
    frame: PIL.Image
        image to be processed (RGBA)
    '''
    assert frame.mode == 'RGBA', "frame must be RGBA"
    array = np.array(frame)
    mask = array[:, :, 3] != 0
    xmin = np.min(np.where(mask)[1])
    xmax = np.max(np.where(mask)[1])
    ymin = np.min(np.where(mask)[0])
    ymax = np.max(np.where(mask)[0])
    array = array[ymin:ymax, xmin:xmax, :]
    return Image.fromarray(array)

def sprite_splitter(sprite_sheet_path, crop_zones, transparent_color=None, show=False):
    '''
    split sprite sheet into single frames
    
    Parameters:
    -----------
    sprite_sheet_path: str
        path to sprite sheet (png)
    
    crop_zones: list of tuples
        crop zones for each frame
        [(x0, y0, x1, y1), ...]
    
    transparent_color: tuple
        color to be replaced with transparent pixels
    
    show: bool
        show image with crop zones
    '''
    path = Path(sprite_sheet_path)

    image = Image.open(sprite_sheet_path)

    # split images in to single frames
    # image.show()
    frames = []


    # add measuring tape
    image_measured = measuring_tape(image.copy())

    color = 'magenta'
    draw = ImageDraw.Draw(image_measured)
    for i, crop_zone in enumerate(crop_zones):
        frame = image.copy().convert("RGBA")
        frame = frame.crop(crop_zone)

        frame = make_transparent(frame, transparent_color=transparent_color)
        frame = strip_frame(frame)
        
        frame_path = path.parent / f"{path.parent.stem}_{i:02d}.png"
        frame.save(frame_path)

        # add rectangle to image
        draw.rectangle(crop_zone, outline=color, width=5)
        # add cross to image)
        draw.line(((crop_zone[0]+crop_zone[2])/2, crop_zone[1], (crop_zone[0]+crop_zone[2])/2, crop_zone[3]), fill=color, width=5)
        draw.line((crop_zone[0], (crop_zone[1]+crop_zone[3])/2, crop_zone[2], (crop_zone[1]+crop_zone[3])/2), fill=color, width=5)

    if show:
        image_measured.show()


def fire():
    sprite_sheet_path = 'assets/effects/fire/fire_sheet.png'

    y = (250, 1700)
    crop_zones = [
        (100, y[0], 380, y[1]),
        (440, y[0], 780, y[1]),
        (830, y[0], 1160, y[1]),
        (1190, y[0], 1600, y[1]),
        (1620, y[0], 2070, y[1]),
        (2100, y[0], 2600, y[1]),
        (2600, y[0], 2980, y[1]),
        (3050, y[0], 3320, y[1]),
        (3365, y[0], 3490, y[1]),
    ]
    sprite_splitter(sprite_sheet_path, crop_zones, transparent_color=(3, 1, 43), show=True)

def viking():
    sprite_sheet_path = 'assets/sprites/viking/viking_sheet.jpg'

    crop_zones = [
        (500, 570, 1450, 1380),
        (1550, 570, 2450, 1380),
        (2500, 570, 3450, 1380),
        (3550, 570, 4500, 1380),
        (4600, 570, 5500, 1380),
        (500, 1750, 1450, 2560),
        (1550, 1750, 2450, 2560),
        (2500, 1750, 3450, 2560),
        (3550, 1750, 4500, 2560),
        (4600, 1750, 5500, 2560),
               ]
    
    sprite_splitter(sprite_sheet_path, crop_zones, transparent_color=(255, 255, 255), show=True)

if __name__ == '__main__':
    viking()