import os
from urllib.request import urlopen


def test_the_service_answers_its_health_path() -> None:
    with urlopen(f"http://127.0.0.1:{os.environ['PORT']}/health") as response:
        assert response.status == 200
