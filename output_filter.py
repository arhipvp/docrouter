import sys
import contextlib

@contextlib.contextmanager
def filter_specific_output():
    """A context manager to filter out specific unwanted output."""
    original_stdout = sys.stdout

    class DummyFile:
        def write(self, x): pass
        def flush(self): pass

    sys.stdout = DummyFile()
    try:
        yield
    finally:
        sys.stdout = original_stdout
