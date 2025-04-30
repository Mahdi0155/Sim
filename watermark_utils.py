from PIL import Image, ImageDraw, ImageFont
import os

def add_watermark(image_path, position_code):
    try:
        base = Image.open(image_path).convert("RGBA")
        watermark_text = "@hottof"

        # ایجاد لایه شفاف برای واترمارک
        txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # فونت و اندازه
        font_size = int(min(base.size) / 12)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, font_size)

        # اندازه متن با textbbox
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        w, h = base.size
        margin = 10

        # موقعیت واترمارک
        positions = {
            "a": (margin, margin),
            "b": (w - text_w - margin, margin),
            "c": (margin, h - text_h - margin),
            "d": (w - text_w - margin, h - text_h - margin),
            "e": ((w - text_w) // 2, (h - text_h) // 2),
        }
        position = positions.get(position_code.lower(), positions["e"])

        # سایه (مشکی نیمه‌شفاف) + متن اصلی سفید
        shadow_offset = 2
        draw.text((position[0] + shadow_offset, position[1] + shadow_offset), watermark_text, font=font, fill=(0, 0, 0, 120))
        draw.text(position, watermark_text, font=font, fill=(255, 255, 255, 200))

        # ترکیب تصویر و لایه واترمارک
        watermarked = Image.alpha_composite(base, txt_layer)

        # ذخیره فایل نهایی
        result_path = image_path.replace(".jpg", "_wm.jpg")
        watermarked.convert("RGB").save(result_path, "JPEG")

        return result_path

    except Exception as e:
        print(f"خطا در ایجاد واترمارک: {e}")
        return image_path
