import pytest

from ssr.config import settings


@pytest.fixture(autouse=True)
def disable_auto_load():
    original = settings.auto_load_vanilla
    settings.auto_load_vanilla = False
    try:
        yield
    finally:
        settings.auto_load_vanilla = original
