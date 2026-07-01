import os
from moviepy import ColorClip, ImageClip

print("MoviePy version:", __import__('moviepy').__version__)

clip = ColorClip(size=(1080, 1920), color=(255, 0, 0), duration=3)
try:
    zoom_clip = clip.resized(lambda t: 1 + 0.05 * t)
    print("Resized with function works.")
    zoom_clip = zoom_clip.cropped(x_center=zoom_clip.w/2, y_center=zoom_clip.h/2, width=1080, height=1920)
    print("Cropped works.")
except Exception as e:
    print("Error:", e)
