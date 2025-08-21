from pathlib import Path
from .config import settings

for d in (settings.inbox_dir, settings.out_dir, settings.ann_dir, settings.tmp_dir):
    Path(d).mkdir(parents=True, exist_ok=True)

class Paths:
    @staticmethod
    def inbox() -> Path: return Path(settings.inbox_dir)
    @staticmethod
    def out() -> Path: return Path(settings.out_dir)
    @staticmethod
    def ann() -> Path: return Path(settings.ann_dir)
    @staticmethod
    def tmp() -> Path: return Path(settings.tmp_dir)
