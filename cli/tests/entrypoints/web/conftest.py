import pytest

from tests.browsers import ENGINES


@pytest.fixture(scope="module", params=ENGINES)
def engine(request: pytest.FixtureRequest) -> str:
    """Each browser test module runs once per engine, each time with a workspace of its own."""
    return request.param
