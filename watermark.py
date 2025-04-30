from PIL import Image, ImageDraw, ImageFont
import os

def add_watermark(input_path, position_code):
    base = Image.open(input_path).convert("RGBA")
    width, height = base.size

    watermark_text = "HotTof"
    font_size = int(width * 0.05)
    font = ImageFont.truetype("arial.ttf", font_size)

    # واترمارک با اوپسیتی
    text_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_layer)

    text_width, text_height = draw.textsize(watermark_text, font=font)
    padding = int(font_size * 0.5)

    positions = {
        'a': (padding, padding),
        'b': (width - text_width - padding, padding),
        'c': (padding, height - text_height - padding),
        'd': (width - text_width - padding, height - text_height - padding),
        'e': ((width - text_width) // 2, (height - text_height) // 2)
    }

    pos = positions.get(position_code, positions['e'])

    # حاشیه مشکی
    shadow_offset = 1
    for dx in [-shadow_offset, 0, shadow_offset]:
        for dy in [-shadow_offset, 0, shadow_offset]:
            if dx != 0 or dy != 0:
                draw.text((pos[0] + dx, pos[1] + dy), watermark_text, font=font, fill=(0, 0, 0, 100))

    # متن سفید با شفافیت
    draw.text(pos, watermark_text, font=font, fill=(255, 255, 255, 80))

    # ترکیب لایه‌ها
    combined = Image.alpha_composite(base, text_layer)
    output_path = input_path.replace(".jpg", "_watermarked.jpg")
    combined.convert("RGB").save(output_path, "JPEG")

    try:
        os.remove(input_path)
    except Exception as e:
        print(f"خطا در حذف فایل اصلی: {e}")

    return output_path
