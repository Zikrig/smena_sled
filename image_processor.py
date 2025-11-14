import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

class ImageProcessor:
    """Класс для обработки изображений с наложением времени"""
    
    @staticmethod
    def add_text_with_outline(image_path, output_path, text_to_draw):
        """
        Добавляет текст с черным контуром на изображение
        Текст занимает половину ширины изображения
        """
        try:
            with Image.open(image_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                draw = ImageDraw.Draw(img)
                
                # Максимальная ширина текста - половина ширины изображения
                max_text_width = img.width // 2
                
                # Разбиваем текст на строки, если нужно
                lines = text_to_draw.split('\n')
                
                # Начальный размер шрифта
                font_size = max(20, img.height // 20)
                font = None
                
                # Пробуем найти доступные шрифты
                font_candidates = [
                    "arial.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/System/Library/Fonts/SFNSDisplay.ttf"  # macOS
                ]
                
                # Подбираем размер шрифта, чтобы текст помещался в половину ширины
                while font_size >= 12:  # Минимальный размер шрифта
                    # Пробуем найти шрифт
                    for candidate in font_candidates:
                        try:
                            font = ImageFont.truetype(candidate, font_size)
                            break
                        except:
                            continue
                    
                    if font is None:
                        font = ImageFont.load_default()
                    
                    # Проверяем ширину самой длинной строки
                    max_line_width = 0
                    line_heights = []
                    
                    for line in lines:
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                        line_height = bbox[3] - bbox[1]
                        line_heights.append(line_height)
                        max_line_width = max(max_line_width, line_width)
                    
                    # Если текст помещается в половину ширины, выходим из цикла
                    if max_line_width <= max_text_width:
                        break
                    
                    # Уменьшаем размер шрифта
                    font_size -= 1
                
                # Вычисляем общую высоту текста
                total_height = sum(line_heights) + (len(lines) - 1) * (font_size // 4)
                
                # Позиция текста (центр правой половины изображения)
                text_x = img.width // 2 + (max_text_width - max_line_width) // 2
                text_y = img.height - total_height - 20
                
                # Рисуем текст с черным контуром
                y_offset = text_y
                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    
                    # Центрируем каждую строку в правой половине
                    line_x = text_x + (max_text_width - line_width) // 2
                    
                    # Рисуем обводку (черный цвет в 8 направлениях)
                    for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), 
                                  (-1, 0), (1, 0), (0, -1), (0, 1)]:
                        draw.text((line_x + dx, y_offset + dy), line, font=font, fill=(0, 0, 0))
                    
                    # Рисуем основной текст (белый цвет)
                    draw.text((line_x, y_offset), line, font=font, fill=(255, 255, 255))
                    
                    y_offset += line_heights[i] + (font_size // 4)
                
                img.save(output_path, format='JPEG', quality=95)
                
        except Exception as e:
            raise Exception(f"Ошибка обработки изображения: {e}")