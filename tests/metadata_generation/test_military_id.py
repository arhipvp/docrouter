import asyncio
from typing import Any, Dict

from metadata_generation import generate_metadata, MetadataAnalyzer


class DummyAnalyzer(MetadataAnalyzer):
    async def analyze(
        self,
        text: str,
        folder_tree: Dict[str, Any] | None = None,
        file_info: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {"prompt": None, "raw_response": None, "metadata": {}}


def test_person_extracted_from_military_id():
    text = (
        "ВОЕННЫЙ БИЛЕТ\n"
        "Фамилия: Петров\n"
        "Имя: Иван\n"
        "Отчество: Сергеевич\n"
    )
    result = asyncio.run(generate_metadata(text, analyzer=DummyAnalyzer()))
    assert result["metadata"].person
