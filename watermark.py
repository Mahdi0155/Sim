from PIL import Image, ImageDraw, ImageFont
import os

def add_watermark(image_path, position_code):
    # بارگذاری تصویر اصلی
    original = Image.open(image_path).convert("RGBA")
    width, height = original.size

    # بارگذاری فونت (شما باید فایل فونت .ttf را داشته باشید)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'  # یا مسیر فونت خودتان
    font_size = 50
    
    # چک کردن دسترسی به فونت
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"فونت در مسیر {font_path} یافت نشد")
    
    font = ImageFont.truetype(font_path, font_size)

    # تنظیمات برای واترمارک
    watermark_text = "HotTof"
    opacity = 77  # 30% opacity
    watermark_color = (255, 255, 255, opacity)  # رنگ سفید با اوپسیتی 30%
    border_color = (0, 0, 0)  # حاشیه مشکی

    # ساخت تصویر جدید با پس‌زمینه شفاف
    watermark = Image.new("RGBA", original.size)
    watermark.paste(original, (0, 0))

    # ایجاد یک Draw object برای رسم واترمارک
    draw = ImageDraw.Draw(watermark, "RGBA")

    # محاسبه موقعیت واترمارک بر اساس پارامتر position_code
    margin = 10  # فاصله از لبه‌های تصویر

    if position_code == 'a':  # بالای سمت چپ
        position = (margin, margin)
    elif position_code == 'b':  # بالای سمت راست
        position = (width - font.getsize(watermark_text)[0] - margin, margin)
    elif position_code == 'c':  # پایین سمت چپ
        position = (margin, height - font.getsize(watermark_text)[1] - margin)
    elif position_code == 'd':  # پایین سمت راست
        position = (width - font.getsize(watermark_text)[0] - margin, height - font.getsize(watermark_text)[1] - margin)
    elif position_code == 'e':  # وسط
        position = (width // 2 - font.getsize(watermark_text)[0] // 2, height // 2 - font.getsize(watermark_text)[1] // 2)
    else:
        raise ValueError("کد موقعیت واترمارک نامعتبر است. از 'a', 'b', 'c', 'd' یا 'e' استفاده کنید.")
    
    # رسم حاشیه (Border)
    border_offset = 2
    for dx in range(-border_offset, border_offset + 1):
        for dy in range(-border_offset, border_offset + 1):
            if dx != 0 or dy != 0:
                draw.text((position[0] + dx, position[1] + dy), watermark_text, font=font, fill=border_color)

    # رسم متن اصلی واترمارک
    draw.text(position, watermark_text, font=font, fill=watermark_color)

    # ترکیب تصویر اصلی و واترمارک
    watermarked_image = Image.alpha_composite(original.convert("RGBA"), watermark)

    # ذخیره تصویر نهایی
    output_path = image_path.replace(".jpg", "_watermarked.jpg").replace(".png", "_watermarked.png")
    watermarked_image.save(output_path)

    # تبدیل مجدد تصویر به فرمت JPG
    final_image = watermarked_image.convert("RGB")
    final_image_path = output_path.replace(".png", ".jpg")
    final_image.save(final_image_path)

    # حذف فایل موقت PNG (در صورتی که فرمت PNG باشد)
    if output_path.endswith(".png"):
        os.remove(output_path)

    return final_image_path
