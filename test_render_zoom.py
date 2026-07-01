import os
from moviepy import ColorClip

clip = ColorClip(size=(1080, 1920), color=(255, 0, 0), duration=1)
zoom_clip = clip.resized(lambda t: 1 + 0.05 * t)
zoom_clip = zoom_clip.cropped(x_center=zoom_clip.w/2, y_center=zoom_clip.h/2, width=1080, height=1920)

zoom_clip.write_videofile("test_zoom.mp4", fps=30)
print("Render successful.")
