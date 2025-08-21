from pathlib import Path
import subprocess

IMG_EXT = {".jpg",".jpeg",".png",".tif",".tiff"}

def to_single_pdf(input_paths: list[Path], out_pdf: Path) -> None:
    imgs = [p for p in input_paths if p.suffix.lower() in IMG_EXT]
    pdfs = [p for p in input_paths if p.suffix.lower() == ".pdf"]
    if pdfs and not imgs:
        out_pdf.write_bytes(pdfs[0].read_bytes()); return
    if imgs:
        args = ["img2pdf", *[str(p) for p in sorted(imgs)], "-o", str(out_pdf)]
        subprocess.check_call(args); return
    out_pdf.write_bytes(b"")
