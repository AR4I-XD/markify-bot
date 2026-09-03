import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs("assets", exist_ok=True)

# Create 600x180 transparent badge for default logo
img = Image.new("RGBA", (600, 180), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Rounded rectangle background with semi-transparent dark-gray
bg_box = [10, 10, 590, 170]
draw.rounded_rectangle(bg_box, radius=35, fill=(20, 24, 33, 200), outline=(255, 255, 255, 120), width=3)

# Inner accent dot
draw.ellipse([45, 65, 95, 115], fill=(79, 142, 247, 240))
draw.polygon([(65, 75), (85, 90), (65, 105)], fill=(255, 255, 255, 255))

# Text MARKIFY
# If default font, we can draw neat text
draw.text((120, 52), "MARKIFY", fill=(255, 255, 255, 240), font_size=58)
draw.text((125, 118), "PHOTO WATERMARK", fill=(180, 195, 220, 200), font_size=20)

img.save("assets/default_logo.png", "PNG")
print("Saved assets/default_logo.png")
