import tkinter as tk
from tkinter.filedialog import askopenfile
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# ——— Маркеры для разделения текста и изображений ———
MARKER_IMAGE_START = 999999999
MARKER_IMAGE_END   = 999999998

# ——— Настройка окна ———
root = tk.Tk()
root.title("PDF ↔ Числа (с изображениями)")
root.geometry("600x550")

canvas = tk.Canvas(root, width=600, height=300)
canvas.grid(columnspan=3, rowspan=3)

try:
    logo = Image.open('logo.png')
    logo = ImageTk.PhotoImage(logo)
    logo_label = tk.Label(image=logo)
    logo_label.image = logo
    logo_label.grid(column=1, row=0)
except:
    pass

instructions = tk.Label(root, text="Выберите действие:", font="Raleway 14")
instructions.grid(columnspan=3, column=0, row=1)

status = tk.Label(root, text="", font="Raleway 10", fg="gray")
status.grid(columnspan=3, column=0, row=4)

# ——— Регистрация шрифта для reportlab ———
def register_font():
    font_name = None
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
        font_name = 'Arial'
    except:
        try:
            pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
            font_name = 'DejaVu'
        except:
            import glob
            ttf_files = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True) + \
                        glob.glob("C:/Windows/Fonts/*.ttf")
            if ttf_files:
                pdfmetrics.registerFont(TTFont('CustomFont', ttf_files[0]))
                font_name = 'CustomFont'
            else:
                font_name = 'Helvetica'  # fallback
    return font_name

FONT_NAME = register_font()

# ——— Функция: PDF → числа ———
def pdf_to_numbers():
    file = askopenfile(parent=root, mode='rb', title="Выберите PDF-файл",
                       filetypes=[("PDF files", "*.pdf")])
    if not file:
        return

    status.config(text="Читаю PDF (текст + изображения)...")
    root.update()

    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        numbers = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # — Извлекаем текст страницы —
            text = page.get_text()
            for ch in text:
                numbers.append(ord(ch))

            # — Извлекаем изображения со страницы —
            images = page.get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]  # 'png', 'jpeg', etc.

                # Кодируем расширение в число (1=PNG, 2=JPEG, 3=GIF, 4=TIFF, 5=WEBP, 0=другое)
                ext_map = {'png': 1, 'jpeg': 2, 'jpg': 2, 'gif': 3, 'tiff': 4, 'webp': 5}
                ext_code = ext_map.get(image_ext, 0)

                # Сохраняем размеры оригинального изображения (прямо из xref)
                # fitz не даёт размеров напрямую, получим через PIL
                pil_img = Image.open(io.BytesIO(image_bytes))
                width, height = pil_img.size

                # Маркер начала изображения
                numbers.append(MARKER_IMAGE_START)
                # Метаданные: ширина, высота, код формата
                numbers.append(width)
                numbers.append(height)
                numbers.append(ext_code)
                # Количество байтов изображения
                numbers.append(len(image_bytes))
                # Сами байты (каждое число от 0 до 255)
                for byte in image_bytes:
                    numbers.append(byte)
                # Маркер конца изображения
                numbers.append(MARKER_IMAGE_END)

        doc.close()

        # Сохраняем на рабочий стол
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        save_path = os.path.join(desktop, "pdf_as_numbers.txt")

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(" ".join(str(n) for n in numbers))

        status.config(text=f"✅ Готово! Файл сохранён:\n{save_path}")
        messagebox.showinfo("Успех", f"PDF (текст + {sum(len(page.get_images()) for page in doc)} изображений) преобразован в числа.\nСохранено:\n{save_path}")

    except Exception as e:
        status.config(text="❌ Ошибка")
        messagebox.showerror("Ошибка", str(e))
    finally:
        file.close()

# ——— Функция: числа → PDF ———
def numbers_to_pdf():
    file = askopenfile(parent=root, mode='r', encoding='utf-8',
                       title="Выберите файл с числами (.txt)",
                       filetypes=[("Text files", "*.txt")])
    if not file:
        return

    status.config(text="Читаю числа и восстанавливаю PDF...")
    root.update()

    try:
        content = file.read()
        numbers = [int(x) for x in content.strip().split()]

        # Парсим числа
        output_pdf_path = os.path.join(os.path.expanduser("~"), "Desktop", "restored_from_numbers.pdf")
        c = pdf_canvas.Canvas(output_pdf_path, pagesize=A4)
        c.setFont(FONT_NAME, 12)

        width, height = A4
        y = height - 50
        x = 50

        i = 0
        while i < len(numbers):
            if numbers[i] == MARKER_IMAGE_START:
                # Начало изображения
                i += 1
                img_width = numbers[i]; i += 1
                img_height = numbers[i]; i += 1
                ext_code = numbers[i]; i += 1
                byte_count = numbers[i]; i += 1

                # Собираем байты
                image_bytes = bytes(numbers[i:i+byte_count])
                i += byte_count

                # Пропускаем маркер конца
                if numbers[i] == MARKER_IMAGE_END:
                    i += 1

                # Декодируем расширение
                ext_map_rev = {1: 'png', 2: 'jpeg', 3: 'gif', 4: 'tiff', 5: 'webp'}
                img_ext = ext_map_rev.get(ext_code, 'png')

                # Если места на странице мало — новая страница
                if y < img_height + 30:
                    c.showPage()
                    c.setFont(FONT_NAME, 12)
                    y = height - 50

                # Сохраняем изображение во временный файл и вставляем в PDF
                temp_img_path = f"/tmp/temp_img.{img_ext}"
                with open(temp_img_path, "wb") as f:
                    f.write(image_bytes)

                # Масштабируем, если слишком большое
                max_w = width - 100
                max_h = y - 50
                scale = min(1.0, max_w / img_width, max_h / img_height)
                draw_w = img_width * scale
                draw_h = img_height * scale

                c.drawImage(temp_img_path, x, y - draw_h, width=draw_w, height=draw_h)
                y -= (draw_h + 15)
                os.remove(temp_img_path)

            else:
                # Обычный текст
                ch = chr(numbers[i])
                i += 1

                if ch == '\n':
                    y -= 15
                    x = 50
                    if y < 50:
                        c.showPage()
                        c.setFont(FONT_NAME, 12)
                        y = height - 50
                else:
                    c.drawString(x, y, ch)
                    x += c.stringWidth(ch, FONT_NAME, 12)
                    if x > width - 50:
                        x = 50
                        y -= 15
                        if y < 50:
                            c.showPage()
                            c.setFont(FONT_NAME, 12)
                            y = height - 50

        c.save()

        status.config(text=f"✅ Готово! PDF сохранён:\n{output_pdf_path}")
        messagebox.showinfo("Успех", f"Числа преобразованы обратно в PDF (с изображениями).\nСохранено:\n{output_pdf_path}")

    except Exception as e:
        status.config(text="❌ Ошибка")
        messagebox.showerror("Ошибка", str(e))
    finally:
        file.close()

# ——— Кнопки ———
btn_pdf_to_num = tk.Button(root, text="📄 PDF → Числа", command=pdf_to_numbers,
                           font="Raleway", bg="#20bebe", fg="white", height=2, width=20)
btn_pdf_to_num.grid(column=0, row=2, padx=10, pady=10)

btn_num_to_pdf = tk.Button(root, text="🔢 Числа → PDF", command=numbers_to_pdf,
                           font="Raleway", bg="#b020be", fg="white", height=2, width=20)
btn_num_to_pdf.grid(column=2, row=2, padx=10, pady=10)

canvas_bottom = tk.Canvas(root, width=600, height=100)
canvas_bottom.grid(columnspan=3)

root.mainloop()
