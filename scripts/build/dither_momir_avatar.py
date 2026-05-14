# Dither the local momir_vig.jpeg for thermal printing.
# Output: images/avatar_images_dithered/momir_avatar.bmp
from PIL import Image
from pathlib import Path

PRINTER_WIDTH = 384

# Load local source image
src = Path(__file__).parent.parent.parent / "momir_vig.jpeg"
img = Image.open(src).convert("RGB")

# Resize to printer width before dithering (preserves aspect ratio)
aspect = img.height / img.width
new_h = int(PRINTER_WIDTH * aspect)
img = img.resize((PRINTER_WIDTH, new_h), Image.Resampling.LANCZOS)

# Convert to grayscale, then dither (Floyd-Steinberg)
dithered = img.convert("L").convert("1")

# Save as BMP (matches what the printer expects)
dst = Path("images_dithered/avatar/momir_avatar.bmp")
dst.parent.mkdir(parents=True, exist_ok=True)
dithered.save(dst)
print(f"Saved dithered avatar image to {dst} ({PRINTER_WIDTH}x{new_h})")
