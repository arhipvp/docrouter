import asyncio
import time
import threading
from pathlib import Path

import pytest

from services import directory_processor as dp


def test_process_input_directory_uses_semaphore_and_threads(tmp_path, monkeypatch):
    input_dir = tmp_path / "in"
    dest_dir = tmp_path / "out"
    input_dir.mkdir()
    dest_dir.mkdir()

    for i in range(6):
        (input_dir / f"f{i}.txt").write_text("content")

    # Stub out heavy functions
    monkeypatch.setattr(dp, "extract_text", lambda p: "text")

    async def fake_generate_metadata(text, folder_tree=None, folder_index=None):
        return {"metadata": {"category": "test"}, "prompt": None, "raw_response": None}

    monkeypatch.setattr(dp.metadata_generation, "generate_metadata", fake_generate_metadata)
    monkeypatch.setattr(dp, "get_folder_tree", lambda dest_root: ({}, {}))
    monkeypatch.setattr(
        dp,
        "place_file",
        lambda path, meta_dict, dest_base, dry_run, needs_new_folder, confirm_callback: (
            dest_dir / path.name,
            [],
            True,
        ),
    )

    active = 0
    max_active = 0
    threads = set()

    def fake_add_file(*args, **kwargs):
        nonlocal active, max_active
        threads.add(threading.current_thread().name)
        active += 1
        max_active = max(max_active, active)
        time.sleep(0.05)
        active -= 1

    monkeypatch.setattr(dp.database, "add_file", fake_add_file)

    asyncio.run(dp.process_input_directory(input_dir, dest_dir))

    main_thread = threading.current_thread().name
    assert max_active <= 5
    assert all(t != main_thread for t in threads)
