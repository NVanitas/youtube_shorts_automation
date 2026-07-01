import math
from PIL import Image
import random
import os

def generate_cinematic_grain(filepath, width=1080, height=1920):
    """Generates a static film grain noise image to be used as an overlay."""
    print("Generating cinematic film grain overlay...")
    # Create a new grayscale image
    img = Image.new('L', (width, height))
    pixels = img.load()
    
    # Fill with random noise (darker gray values for subtle grain)
    for x in range(width):
        for y in range(height):
            # values between 100 and 155 to give a medium-dark gritty texture
            pixels[x, y] = random.randint(100, 155)
            
    img.save(filepath)
    print(f"Film grain overlay saved at: {filepath}")

def generate_cinematic_vignette(filepath):
    """Generates a radial vignette overlay (dark edges, transparent center)."""
    print("Generating cinematic vignette overlay...")
    width, height = 1080, 1920
    img = Image.new('RGBA', (width, height), (0,0,0,0))
    
    cx = width / 2
    cy = height / 2
    max_dist = math.sqrt(cx**2 + cy**2)
    
    # We create a radial gradient
    for y in range(height):
        for x in range(width):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            # Normalize distance
            norm = dist / max_dist
            # Exponential curve for smooth falloff (only affecting the outer ~40%)
            if norm > 0.4:
                alpha = int(255 * ( (norm - 0.4) / 0.6 ) ** 1.5)
                # Cap at ~85% opacity at the very corners
                alpha = min(220, alpha)
                img.putpixel((x, y), (0, 0, 0, alpha))
                
    img.save(filepath)
    print(f"Vignette overlay saved at: {filepath}")

def generate_cinematic_particles(filepath):
    """Generates a 2x tall transparent image with scattered dust particles to be animated moving upwards."""
    print("Generating cinematic particles overlay...")
    import random
    from PIL import ImageDraw
    width, height = 1080, 1920 * 2 # Double height for seamless scrolling
    img = Image.new('RGBA', (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    num_particles = 150
    for _ in range(num_particles):
        x = random.randint(0, width)
        y = random.randint(0, height)
        # Random size 2-6 pixels
        size = random.randint(2, 6)
        # Random opacity 10-60
        alpha = random.randint(10, 60)
        draw.ellipse([x, y, x+size, y+size], fill=(255, 255, 255, alpha))
        
    # Apply a slight blur so they look like out-of-focus dust
    from PIL import ImageFilter
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    img.save(filepath)
    print(f"Particles overlay saved at: {filepath}")

def generate_light_leak(filepath):
    """Generates a warm orange/red light leak gradient for transition flashes."""
    print("Generating cinematic light leak overlay...")
    width, height = 1080, 1920
    img = Image.new('RGBA', (width, height), (0,0,0,0))
    
    # We create a large off-center radial gradient (orange/red)
    cx = width * 0.8
    cy = height * 0.2
    max_dist = math.sqrt(width**2 + height**2) * 0.7
    
    for y in range(0, height, 4): # step 4 for performance, then resize
        for x in range(0, width, 4):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            norm = min(1.0, dist / max_dist)
            # Intensity falls off smoothly
            intensity = (1.0 - (norm ** 1.5))
            if intensity > 0:
                # Orange-red tint
                r = 255
                g = int(120 * intensity)
                b = int(20 * intensity)
                alpha = int(180 * intensity) # Max 180 opacity
                img.putpixel((x, y), (r, g, b, alpha))
                
    # Scale up to fill the gaps from step=4
    img = img.resize((width, height), Image.Resampling.BICUBIC)
    
    from PIL import ImageFilter
    img = img.filter(ImageFilter.GaussianBlur(radius=50)) # Massive blur for smooth light
    img.save(filepath)
    print(f"Light leak overlay saved at: {filepath}")

if __name__ == "__main__":
    generate_cinematic_grain("assets/grain.png")
    generate_cinematic_vignette("assets/vignette.png")
    generate_cinematic_particles("assets/particles.png")
    generate_light_leak("assets/light_leak.png")
