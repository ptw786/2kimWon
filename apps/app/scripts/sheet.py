"""screenshots/ 안의 화면을 한 장으로 모아 본다(눈으로 비교용). 실행: python3 scripts/sheet.py <출력 폴더>"""
import glob
import sys
from pathlib import Path
from PIL import Image

shots = Path(__file__).resolve().parent.parent / "screenshots"
out = Path(sys.argv[1] if len(sys.argv) > 1 else shots)
for tag in ["390x844", "330x700"]:
    files = sorted(glob.glob(str(shots / f"{tag}-*.png")))
    ims = [Image.open(f) for f in files]
    w, h = ims[0].width // 2, ims[0].height // 2
    ims = [i.resize((w, h)) for i in ims]
    cols = 6
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols - 1) * 10, rows * h + (rows - 1) * 10), "#888")
    for k, i in enumerate(ims):
        sheet.paste(i, ((k % cols) * (w + 10), (k // cols) * (h + 10)))
    sheet.save(out / f"sheet-{tag}.png")
