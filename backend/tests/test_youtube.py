import pytest

from app.integrations import youtube
from app.integrations.youtube import YouTubeClient, YouTubeError, parse_duration, parse_video_id
from tests.youtube_fixtures import ENGLISH, LUDO, OFFTOPIC, OTHER, youtube_transport

VALID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "value",
    [
        f"https://www.youtube.com/watch?v={VALID}",
        f"https://www.youtube.com/watch?v={VALID}&t=42s&list=PL1",
        f"youtube.com/watch?v={VALID}",
        f"https://youtu.be/{VALID}?si=abc",
        f"https://m.youtube.com/watch?v={VALID}",
        f"https://www.youtube.com/embed/{VALID}",
        f"https://www.youtube-nocookie.com/embed/{VALID}",
        f"https://www.youtube.com/shorts/{VALID}",
        f"https://www.youtube.com/live/{VALID}",
        f"  {VALID}  ",
    ],
)
def test_parse_video_id(value):
    assert parse_video_id(value) == VALID


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=trop-court",
        "https://www.youtube.com/channel/UC1234567890",
        "pas un lien",
    ],
)
def test_parse_video_id_rejects_other_links(value):
    assert parse_video_id(value) is None


def test_parse_duration():
    assert parse_duration("PT12M30S") == 750
    assert parse_duration("PT1H2M") == 3720
    assert parse_duration("PT45S") == 45
    assert parse_duration("P0D") is None
    assert parse_duration(None) is None


@pytest.fixture(autouse=True)
def _clear_channel_cache():
    youtube._channel_ids.clear()


def test_suggest_puts_priority_channel_first_and_filters():
    client = YouTubeClient("cle-secrete", transport=youtube_transport())
    videos = client.suggest("Catan", ["Ludochrono"])
    ids = [v.youtube_id for v in videos]
    assert ids == [LUDO, OTHER]  # ni l'anglais ni le hors-sujet
    assert videos[0].priority and not videos[1].priority
    assert videos[0].channel == "Ludochrono" and videos[0].duration_seconds == 750
    assert ENGLISH not in ids and OFFTOPIC not in ids


def test_channel_is_resolved_once_and_exactly():
    client = YouTubeClient("cle-secrete", transport=youtube_transport())
    assert client.find_channel("Ludochrono") == "UC-ludo"  # et non le « fan club »
    assert youtube._channel_ids == {"ludochrono": "UC-ludo"}


def test_unknown_channel_is_skipped():
    client = YouTubeClient("cle-secrete", transport=youtube_transport())
    ids = [v.youtube_id for v in client.suggest("Catan", ["Chaîne inconnue"])]
    assert LUDO in ids


@pytest.mark.parametrize(
    ("reason", "status", "message"),
    [
        ("quotaExceeded", 403, "quota"),
        ("keyInvalid", 400, "YOUTUBE_API_KEY"),
        ("backendError", 500, "erreur"),
    ],
)
def test_errors_are_french_and_hide_the_key(reason, status, message):
    client = YouTubeClient("cle-secrete", transport=youtube_transport(reason, status))
    with pytest.raises(YouTubeError, match=message) as error:
        client.suggest("Catan", [])
    assert "cle-secrete" not in str(error.value)


def test_network_failure_hides_the_key():
    import httpx

    def boom(request):
        raise httpx.ConnectError(f"échec sur {request.url}")

    client = YouTubeClient("cle-secrete", transport=httpx.MockTransport(boom))
    with pytest.raises(YouTubeError) as error:
        client.suggest("Catan", [])
    assert "cle-secrete" not in str(error.value)
