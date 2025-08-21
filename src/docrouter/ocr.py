import subprocess
from pathlib import Path
from .config import settings

class OCRError(Exception):
    pass

def run_ocr(pdf_in: Path, out_txt: Path) -> None:
    cmd = ["ocrmypdf","-l", settings.ocr_lang,"--sidecar", str(out_txt), str(pdf_in), str(pdf_in.with_suffix(".ocr.pdf"))]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise OCRError(p.stderr)
