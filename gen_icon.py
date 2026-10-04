from PIL import Image, ImageDraw, ImageFont
import os, struct, io

ico_path = r"E:\Code\AI_Projects\docx2txt_gui\src-tauri\icons\icon.ico"
os.makedirs(os.path.dirname(ico_path), exist_ok=True)

sizes = [256, 128, 64, 48, 32, 16]
imgs = []

for sz in sizes:
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 背景圆角矩形
    r = sz // 8
    draw.rounded_rectangle([(0, 0), (sz - 1, sz - 1)], radius=r, fill=(37, 99, 235))

    # 画一个 doc 文件图形
    pad = sz // 5
    doc_x, doc_y = pad, pad
    doc_w, doc_h = sz - pad * 2, sz - pad * 2

    # 文件背景
    draw.rounded_rectangle(
        [(doc_x, doc_y), (doc_x + doc_w, doc_y + doc_h)],
        radius=sz // 16,
        fill=(255, 255, 255, 240)
    )

    # 顶部蓝条（模拟折角）
    bar_h = doc_h // 4
    draw.rectangle(
        [(doc_x, doc_y), (doc_x + doc_w, doc_y + bar_h)],
        fill=(37, 99, 235)
    )

    # 文字 "文"
    try:
        font_size = max(sz // 3, 8)
        font = ImageFont.truetype("msyh.ttc", font_size)
    except:
        try:
            font = ImageFont.truetype("simhei.ttf", font_size)
        except:
            font = ImageFont.load_default()

    text = "文"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = doc_x + (doc_w - tw) // 2
    ty = doc_y + bar_h + (doc_h - bar_h - th) // 2
    draw.text((tx, ty), text, font=font, fill=(37, 99, 235))

    imgs.append(img.copy())

# 生成 ICO 文件
def save_ico(imgs, path):
    with open(path, 'wb') as f:
        # ICO header
        f.write(struct.pack('<HHH', 0, 1, len(imgs)))
        offset = 6 + 16 * len(imgs)
        entries = []
        for img in imgs:
            w = img.width if img.width < 256 else 0
            h = img.height if img.height < 256 else 0
            entries.append((w, h, 0, 0, 1, 32, offset, img.size[0] * img.size[1] * 4))
        for (w, h, _, _, _, _, off, sz) in entries:
            f.write(struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, sz, off))
        for img in imgs:
            f.write(img.tobytes())

save_ico(imgs, ico_path)
print(f"Icon created: {ico_path} ({os.path.getsize(ico_path)} bytes)")
