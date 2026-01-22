import sys
from PIL import Image
from pathlib import Path

# Получение пути к изображению
if len(sys.argv) > 1:
    input_path = Path(sys.argv[1]).expanduser().resolve()
else:
    raw_input_path = input("Введите путь к изображению: ").strip()
    if (raw_input_path.startswith("'") and raw_input_path.endswith("'")) or (
            raw_input_path.startswith('"') and raw_input_path.endswith('"')):
        raw_input_path = raw_input_path[1:-1]
    input_path = Path(raw_input_path).expanduser().resolve()

# Получение пути к ватермарке (по умолчанию ../watermark.png)
wm_input = input("Введите путь к файлу ватермарки (по умолчанию ../watermark.png) или NO: ").strip()
if (wm_input.startswith("'") and wm_input.endswith("'")) or (wm_input.startswith('"') and wm_input.endswith('"')):
    wm_input = wm_input[1:-1]
watermark_path = Path(wm_input if wm_input else "../watermark.png").expanduser().resolve()

isWatermarkProvided = wm_input.lower() != 'no'

if not input_path.is_file():
    raise FileNotFoundError(f"Файл не найден: {input_path}")
if isWatermarkProvided and not watermark_path.is_file():
    raise FileNotFoundError(f"Файл ватермарки не найден: {watermark_path}")

# Директория для вывода рядом с исходным изображением
OUTPUT = input_path.parent / ("cutted " + input_path.stem)
H = 1440

# Диапазон допустимых соотношений сторон (4:5–1.91:1)
AR_MIN, AR_MAX = 4 / 5, 1.91

# Открытие изображения и ресайз
full_img = Image.open(input_path).convert("RGBA")
scale = H / full_img.height
W = round(full_img.width * scale)
full_img = full_img.resize((W, H), Image.LANCZOS)

# Подбор разбиения — выбираем максимально вертикальное (минимальное AR)
best = None
for N in range(1, W + 1):
    tile_w = W // N
    if tile_w <= 0:
        break
    ar = tile_w / H
    if AR_MIN <= ar <= AR_MAX:
        # Критерий: чем меньше AR, тем вертикальнее
        if best is None or (ar, -tile_w) < (best['ar'], -best['tile_w']):
            best = {'N': N, 'tile_w': tile_w, 'ar': ar}

if not best:
    raise RuntimeError("Не удалось подобрать ширину тайла в диапазоне соотношений 4:5–1.91:1")

watermark = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
if isWatermarkProvided:
    # Загружаем ватермарку и подготавливаем
    watermark = Image.open(watermark_path).convert("RGBA")
    wm_scale_factor = (H * 0.15) / watermark.height
    wm_width = int(watermark.width * wm_scale_factor)
    wm_height = int(watermark.height * wm_scale_factor)
    watermark = watermark.resize((wm_width, wm_height), Image.LANCZOS)

# Нарезка с добавлением ватермарки к каждой части
OUTPUT.mkdir(parents=True, exist_ok=True)
for i in range(best['N']):
    box = (i * best['tile_w'], 0, (i + 1) * best['tile_w'], H)
    tile = full_img.crop(box).convert("RGBA")

    if isWatermarkProvided:
        # Позиция ватермарки — 5px от правого и нижнего края
        pos = (tile.width - wm_width - 5, tile.height - wm_height - 5)
        tile.alpha_composite(watermark, dest=pos)

    tile = tile.convert("RGB")
    tile.save(OUTPUT / f"{input_path.stem}_{i + 1:02d}.jpg", quality=95)

print(f"{best['N']} частей по {best['tile_w']}x{H}px (AR={best['ar']:.4f}, диапазон 0.8–1.91)")
