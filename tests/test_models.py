import pytest

from models import Metadata, FileRecord, UploadResponse


def test_metadata_lists_are_independent():
    m1 = Metadata()
    m2 = Metadata()
    assert m1.tags == []
    assert m2.tags == []
    assert m1.tags is not m2.tags
    assert m1.tags_ru is not m2.tags_ru
    assert m1.tags_en is not m2.tags_en


def test_file_record_lists_are_independent():
    fr1 = FileRecord(id="1", filename="a.txt", metadata=Metadata(), path="p1", status="s1")
    fr2 = FileRecord(id="2", filename="b.txt", metadata=Metadata(), path="p2", status="s2")
    assert fr1.tags_ru == [] and fr2.tags_ru == []
    assert fr1.tags_ru is not fr2.tags_ru
    assert fr1.tags_en is not fr2.tags_en
    assert fr1.missing is not fr2.missing
    assert fr1.chat_history is not fr2.chat_history


def test_upload_response_lists_are_independent():
    u1 = UploadResponse(id="1", status="ok")
    u2 = UploadResponse(id="2", status="ok")
    assert u1.tags_ru == [] and u2.tags_ru == []
    assert u1.tags_ru is not u2.tags_ru
    assert u1.tags_en is not u2.tags_en
    assert u1.missing is not u2.missing
