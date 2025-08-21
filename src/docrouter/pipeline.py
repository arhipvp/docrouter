import uuid, json, datetime, re
from pathlib import Path
from langdetect import detect
from .storage import Paths
from .normalize import to_single_pdf
from .ocr import run_ocr
from .translate import translate_text
from .llm import complete

def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "General"

def category_base(category: str, date: str | None, bucket: str | None) -> Path:
    base = Path("/data/Out")
    y = m = None
    if date:
        try:
            dt = datetime.datetime.fromisoformat(date)
            y, m = f"{dt.year:04d}", f"{dt.month:02d}"
        except Exception:
            y = m = None
    b = sanitize(bucket) if bucket else None
    # Mapping
    if category == "purchases_invoices":
        p = base / "Purchases" / "Invoices"
        if y and m: p = p / y / m
        if b: p = p / b
        return p
    if category == "family_utilities":
        p = base / "Family" / "Utilities"
        if b: p = p / b
        if y and m: p = p / y / m
        return p
    if category == "subscriptions":
        p = base / "Subscriptions"
        if b: p = p / b
        if y and m: p = p / y / m
        return p
    if category == "personal_education":
        p = base / "Personal" / "Education"
        if b: p = p / b
        if y: p = p / y
        return p
    if category == "activities":
        p = base / "Activities"
        if b: p = p / b
        if y: p = p / y
        return p
    if category == "travel":
        p = base / "Travel"
        if y: p = p / y
        if b: p = p / b
        return p
    if category == "family_vehicle":
        p = base / "Family" / "Vehicle"
        if b: p = p / b
        return p
    # Personal buckets
    if category == "personal_id":
        return base / "Personal" / "ID"
    if category == "personal_employment":
        return base / "Personal" / "Employment"
    if category == "personal_health":
        return base / "Personal" / "Health"
    if category == "family_marriage":
        return base / "Family" / "Marriage"
    if category == "family_kids":
        return base / "Family" / "Kids"
    if category == "family_housing":
        return base / "Family" / "Housing"
    if category == "family_taxes":
        p = base / "Family" / "Taxes"
        if y: p = p / y
        return p
    if category == "purchases_warranty":
        return base / "Purchases" / "Warranty"
    if category == "purchases_manuals":
        return base / "Purchases" / "Manuals"
    if category == "legal":
        return base / "Legal"
    return base / "Misc"

async def process_upload(paths: list[Path]) -> dict:
    job_id = str(uuid.uuid4())
    work_dir = Paths.tmp() / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1) Normalize → single PDF
    pdf_path = work_dir / "bundle.pdf"
    to_single_pdf(paths, pdf_path)

    # 2) OCR → fulltext
    fulltext = work_dir / "fulltext.txt"
    run_ocr(pdf_path, fulltext)
    text = fulltext.read_text(errors="ignore")

    # 3) Lang + optional translate
    lang = "unknown"
    try:
        lang = detect(text)
    except Exception:
        pass
    translated = text
    if lang.startswith("de"):
        translated = await translate_text(text, source="de", target="ru")

    # 4) LLM notes
    notes_prompt = Path("/app/prompts/notes_prompt.txt").read_text() + "\n\n" + text
    notes = await complete(notes_prompt, max_tokens=600)

    # 5) LLM routing (category/bucket/date/filename_hint)
    routing_prompt = Path("/app/prompts/routing_prompt.txt").read_text() + "\n\n" + text
    raw = await complete(routing_prompt, max_tokens=220)
    try:
        choice = json.loads(raw)
        category = str(choice.get("category") or "misc")
        bucket = choice.get("bucket")
        date = choice.get("date")
        hint = choice.get("filename_hint") or "document"
    except Exception:
        category, bucket, date, hint = "misc", None, None, "document"

    out_dir = category_base(category, date, bucket)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 6) Save
    fname = f"{sanitize(hint)}_{job_id}.pdf"
    final_pdf = out_dir / fname
    final_pdf.write_bytes(pdf_path.read_bytes())

    ann_dir = Paths.ann() / job_id
    ann_dir.mkdir(parents=True, exist_ok=True)
    (ann_dir/"notes.md").write_text(notes)
    (ann_dir/"fulltext.txt").write_text(text)
    (ann_dir/"translation.ru.txt").write_text(translated)
    (ann_dir/"meta.json").write_text(json.dumps({
        "job_id": job_id,
        "lang": lang,
        "category": category,
        "bucket": bucket,
        "date": date,
        "filename": str(final_pdf),
    }, ensure_ascii=False, indent=2))

    return {"job_id": job_id, "category": category, "bucket": bucket, "pdf": str(final_pdf)}
