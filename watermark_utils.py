from PIL import Image, ImageDraw, ImageFont
import os

def add_watermark(image_path, position_code):
    try:
        base = Image.open(image_path).convert("RGBA")
        watermark_text = "@hottof"

        # ایجاد تصویر واترمارک با متن
        txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt)

        font_size = int(min(base.size) / 12)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, font_size)

        text_size = draw.textsize(watermark_text, font=font)
        w, h = base.size
        tw, th = text_size

        margin = 10

        # موقعیت‌های ممکن
        positions = {
            "a": (margin, margin),
            "b": (w - tw - margin, margin),
            "c": (margin, h - th - margin),
            "d": (w - tw - margin, h - th - margin),
            "e": ((w - tw) // 2, (h - th) // 2),
        }

        position = positions.get(position_code.lower(), positions["e"])

        # نوشتن متن واترمارک
        draw.text(position, watermark_text, font=font, fill=(255, 255, 255, 180))  # سفید نیمه‌شفاف

        watermarked = Image.alpha_composite(base, txt)

        # ذخیره فایل
        result_path = image_path.replace(".jpg", "_wm.jpg")
        watermarked.convert("RGB").save(result_path, "JPEG")

        return result_path

    except Exception as e:
        print(f"خطا در ایجاد واترمارک: {e}")
        return image_path
