import tkinter as tk
from tkinter.filedialog import askopenfile
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import io

# ——— Функция: создать изображение из RGB-чисел ———
def create_image_from_rgb(rgb_numbers, target_width=None, target_height=None):
    """
    rgb_numbers: список чисел [R1, G1, B1, R2, G2, B2, ...]
    Возвращает объект Image
    """
    count = len(rgb_numbers) // 3
    if count == 0:
        return None

    # Определяем размеры: ищем близкие к target_width x target_height
    if target_width and target_height:
        tex_width = target_width
        tex_height = target_height
        # Если пикселей не хватает — дополняем чёрным
        needed = tex_width * tex_height
        if count < needed:
            rgb_numbers = rgb_numbers + [0, 0, 0] * (needed - count)
    else:
        # Автоподбор размеров (как в JS коде)
        tex_width = int(count ** 0.5)
        while tex_width >= 1:
            tex_height = (count + tex_width - 1) // tex_width
            if tex_width * tex_height - count < tex_width * ((count + tex_width - 2) // tex_width) - count:
                break
            tex_width -= 1
        tex_width = max(1, int(count ** 0.5))
        tex_height = (count + tex_width - 1) // tex_width
        # Дополняем чёрным
        needed = tex_width * tex_height
        if count < needed:
            rgb_numbers = rgb_numbers + [0, 0, 0] * (needed - count)

    # Создаём изображение
    img = Image.new("RGB", (tex_width, tex_height))
    pixels = img.load()

    idx = 0
    for y in range(tex_height):
        for x in range(tex_width):
            if idx * 3 + 2 < len(rgb_numbers):
                r = rgb_numbers[idx * 3]
                g = rgb_numbers[idx * 3 + 1]
                b = rgb_numbers[idx * 3 + 2]
                pixels[x, y] = (r, g, b)
            idx += 1

    return img

# ——— Настройка окна ———
root = tk.Tk()
root.title("PDF ↔ Числа")
root.geometry("600x550")

canvas = tk.Canvas(root, width=600, height=300)
canvas.grid(columnspan=3, rowspan=3)

# ——— ГЕНЕРИРУЕМ ЛОГОТИП ИЗ ЧИСЕЛ ———
# Здесь вы можете вставить свои RGB-числа
# Пример: простой градиент / узор / или числа из pdf_as_numbers.txt
logo_rgb_data = [
    255, 0, 0,    0, 255, 0,    0, 0, 255,    255, 255, 0,
    0, 255, 255,  255, 0, 255,  128, 128, 128, 255, 128, 0,
    255, 200, 100, 200, 100, 50, 100, 200, 150, 50, 100, 200,
    # Добавьте свои числа — хоть из pdf_as_numbers.txt
]

try:
    logo_img = create_image_from_rgb(logo_rgb_data, target_width=200, target_height=100)
    if logo_img:
        logo_tk = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(image=logo_tk)
        logo_label.image = logo_tk
        logo_label.grid(column=1, row=0)
    else:
        raise Exception("Нет RGB-данных")
except Exception as e:
    # Если не вышло — просто пустое место
    pass

# Инструкция
instructions = tk.Label(root, text="Выберите действие:", font="Raleway 14")
instructions.grid(columnspan=3, column=0, row=1)

status = tk.Label(root, text="", font="Raleway 10", fg="gray")
status.grid(columnspan=3, column=0, row=4)

# ——— Функция: PDF → числа ———
def pdf_to_numbers():
    file = askopenfile(parent=root, mode='rb', title="Выберите PDF-файл",
                       filetypes=[("PDF files", "*.pdf")])
    if not file:
        return

    status.config(text="Читаю PDF...")
    root.update()

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        all_text = ""
        for page in reader.pages:
            all_text += page.extract_text()

        numbers = [str(ord(ch)) for ch in all_text]
        output = " ".join(numbers)

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        save_path = os.path.join(desktop, "pdf_as_numbers.txt")

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(output)

        status.config(text=f"✅ Готово! Файл сохранён:\n{save_path}")
        messagebox.showinfo("Успех", f"PDF преобразован в числа.\nСохранено:\n{save_path}")

    except Exception as e:
        status.config(text="❌ Ошибка")
        messagebox.showerror("Ошибка", str(e))
    finally:
        file.close()

# ——— Функция: числа → PDF ———
def numbers_to_pdf():
    file = askopenfile(parent=root, mode='r', title="Выберите файл с числами (.txt)",
                       filetypes=[("Text files", "*.txt")])
    if not file:
        return

    status.config(text="Читаю числа...")
    root.update()

    try:
        content = file.read()
        code_strings = content.strip().split()
        chars = []
        for s in code_strings:
            if s.strip():
                chars.append(chr(int(s.strip())))
        reconstructed_text = "".join(chars)

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as pdf_canvas

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        save_path = os.path.join(desktop, "restored_from_numbers.pdf")

        c = pdf_canvas.Canvas(save_path, pagesize=A4)
        width, height = A4
        y = height - 50

        line = ""
        for ch in reconstructed_text:
            line += ch
            if len(line) >= 80 or ch == "\n":
                c.drawString(50, y, line)
                y -= 15
                line = ""
                if y < 50:
                    c.showPage()
                    y = height - 50
        if line:
            c.drawString(50, y, line)

        c.save()

        status.config(text=f"✅ Готово! PDF сохранён:\n{save_path}")
        messagebox.showinfo("Успех", f"Числа преобразованы обратно в PDF.\nСохранено:\n{save_path}")

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