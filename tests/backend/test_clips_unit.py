"""
Test Plan
- Partitions: download enabled/disabled, overlay on/off, mp4 vs HTML inputs
- Boundaries: max_clips=0, empty HTML input, missing video src
- Failure modes: download_clip raises ValueError when no mp4 source is found
"""

from pathlib import Path

import pytest

from backend import clips


class _DummyElement:
    def __init__(self, href=None, text=None, src=None):
        self._href = href
        self.text = text
        self._src = src

    def get_attribute(self, name):
        if name == "href":
            return self._href
        if name == "src":
            return self._src
        return None


class _DummyDriver:
    def __init__(self, video_srcs):
        self._video_srcs = iter(video_srcs)
        self.visited = []
        self._last_src = None

    def get(self, url):
        self.visited.append(url)

    def find_elements(self, *_args, **_kwargs):
        return [_DummyElement(href="link-1"), _DummyElement(href="link-2")]

    def find_element(self, _by, selector):
        if selector == ".tw-stat__value":
            return _DummyElement(text="1000")
        try:
            self._last_src = next(self._video_srcs)
        except StopIteration:
            pass
        return _DummyElement(src=self._last_src)

    def quit(self):
        return None


class _DummyWait:
    def until(self, *_args, **_kwargs):
        return None


class _DummyThread:
    def __init__(self, target=None, args=None):
        self._target = target
        self._args = args or ()

    def start(self):
        if self._target:
            self._target(*self._args)

    def join(self):
        return None


class _DummyProcess:
    def __init__(self, target=None, args=None):
        self._target = target
        self._args = args or ()

    def start(self):
        if self._target:
            self._target(*self._args)

    def join(self):
        return None


class _FlakyThread:
    def __init__(self, target=None, args=None):
        self._target = target
        self._args = args or ()
        self._started = False

    def start(self):
        if not self._started:
            self._started = True
            raise ValueError("first start fails")
        if self._target:
            self._target(*self._args)

    def join(self):
        return None


class _DummyOptions:
    def __init__(self):
        self.arguments = []

    def add_argument(self, arg):
        self.arguments.append(arg)


def _noop_urlretrieve(_url, output_path):
    Path(output_path).write_text("downloaded")


def _patch_getclips_common(monkeypatch):
    monkeypatch.setattr(clips, "WebDriverWait", lambda *_args, **_kwargs: _DummyWait())
    monkeypatch.setattr(clips.threading, "Thread", _DummyThread)
    monkeypatch.setattr(clips.urllib.request, "urlretrieve", _noop_urlretrieve)
    monkeypatch.setattr(clips.time, "sleep", lambda *_args, **_kwargs: None)


def test_getclips_downloads_with_mocked_driver(tmp_path, monkeypatch):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    driver = _DummyDriver(["src-1", "src-2"])

    _patch_getclips_common(monkeypatch)

    clips.getclips(
        "tester",
        current_videos_dir=str(tmp_path),
        max_clips=1,
        wait_seconds=1,
        apply_overlay=False,
        driver=driver,
    )

    assert list(tmp_path.glob("*.mp4")), "Expected at least one clip download."


def test_getclips_skips_duplicate_src(tmp_path, monkeypatch):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    driver = _DummyDriver(["src-1", "src-1"])

    _patch_getclips_common(monkeypatch)

    clips.getclips(
        "tester",
        current_videos_dir=str(tmp_path),
        max_clips=2,
        wait_seconds=1,
        apply_overlay=False,
        driver=driver,
    )

    assert len(list(tmp_path.glob("*.mp4"))) == 1


def test_getclips_overlay_path(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    driver = _DummyDriver(["src-1"])
    captured = {"process_args": None, "start_called": False, "join_called": False, "removed": None}

    _patch_getclips_common(monkeypatch)

    class _RecordingProcess(_DummyProcess):
        def __init__(self, target=None, args=None):
            super().__init__(target=target, args=args)
            captured["process_args"] = (target, args)

        def start(self):
            captured["start_called"] = True
            super().start()

        def join(self):
            captured["join_called"] = True
            return super().join()

    monkeypatch.setattr(clips, "Process", _RecordingProcess)
    monkeypatch.setattr(clips, "overlay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(clips.os, "remove", lambda path: captured.__setitem__("removed", path))

    clips.getclips(
        "tester",
        current_videos_dir=str(tmp_path),
        max_clips=1,
        wait_seconds=1,
        apply_overlay=True,
        driver=driver,
    )
    assert captured["process_args"][0] == clips.overlay
    assert captured["process_args"][1] == ("1000", "tester", str(tmp_path))
    assert captured["start_called"] is True
    assert captured["join_called"] is True
    assert captured["removed"].endswith("1000tester0.mp4")


def test_overlay_writes_expected_output(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    captured = {}

    class _DummyTextClip:
        def __init__(self, **_kwargs):
            return None

        def with_duration(self, *_args, **_kwargs):
            return self

        def with_effects(self, *_args, **_kwargs):
            return self

        def with_position(self, *_args, **_kwargs):
            return self

    class _DummyVideoFileClip:
        def __init__(self, source_path):
            captured["source_path"] = source_path

    class _DummyCompositeVideoClip:
        def __init__(self, _clips):
            return None

    class _DummyConcat:
        def write_videofile(self, output_path, **_kwargs):
            captured["output_path"] = output_path

    monkeypatch.setattr(clips, "TextClip", _DummyTextClip)
    monkeypatch.setattr(clips, "VideoFileClip", _DummyVideoFileClip)
    monkeypatch.setattr(clips, "CompositeVideoClip", _DummyCompositeVideoClip)
    monkeypatch.setattr(clips, "concatenate_videoclips", lambda _clips: _DummyConcat())

    clips.overlay("123", "streamer\n", str(tmp_path))

    assert captured["source_path"].endswith("123streamer0.mp4")
    assert captured["output_path"].endswith("123streamer0.5.mp4")


def test_getclips_uses_headless_env_and_gecko_path(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    captured = {"service_path": None, "options": None, "quit_called": False}

    def _dummy_service(*_args, **kwargs):
        captured["service_path"] = kwargs.get("executable_path")
        return "service"

    def _dummy_firefox(service=None, options=None):
        captured["options"] = options

        class _WrappedDriver(_DummyDriver):
            def quit(self):
                captured["quit_called"] = True
                return None

        wrapped = _WrappedDriver(["src-1"])
        return wrapped

    monkeypatch.setenv("HEADLESS", "1")
    monkeypatch.setenv("GECKODRIVER_PATH", "C:\\fake\\geckodriver.exe")
    monkeypatch.setattr(clips.os.path, "exists", lambda _path: True)
    monkeypatch.setattr(clips, "Service", _dummy_service)
    monkeypatch.setattr(clips.webdriver, "FirefoxOptions", _DummyOptions)
    monkeypatch.setattr(clips.webdriver, "Firefox", _dummy_firefox)
    monkeypatch.setattr(clips, "WebDriverWait", lambda *_args, **_kwargs: _DummyWait())
    monkeypatch.setattr(clips.threading, "Thread", _FlakyThread)
    monkeypatch.setattr(clips.urllib.request, "urlretrieve", _noop_urlretrieve)
    monkeypatch.setattr(clips.time, "sleep", lambda *_args, **_kwargs: None)

    clips.getclips(
        "tester",
        current_videos_dir=str(tmp_path),
        max_clips=1,
        wait_seconds=1,
        apply_overlay=False,
        driver=None,
    )

    assert captured["service_path"] == "C:\\fake\\geckodriver.exe"
    assert "-headless" in captured["options"].arguments
    assert captured["quit_called"] is True


def test_getclips_skips_missing_video_src(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    driver = _DummyDriver([None])
    captured = {"downloads": 0}

    _patch_getclips_common(monkeypatch)
    monkeypatch.setattr(
        clips.urllib.request,
        "urlretrieve",
        lambda *_args, **_kwargs: captured.__setitem__("downloads", captured["downloads"] + 1),
    )

    clips.getclips(
        "tester",
        current_videos_dir=str(tmp_path),
        max_clips=1,
        wait_seconds=1,
        apply_overlay=False,
        driver=driver,
    )

    assert not list(tmp_path.glob("*.mp4"))
    assert captured["downloads"] == 0
    assert any("/clips?filter=clips&range=24hr" in url for url in driver.visited)
    assert any("link-1" in url for url in driver.visited)


@pytest.mark.parametrize(
    ("html_text", "expected"),
    [
        (
            '<video src="https://example.com/video-1080.mp4?token=abc&amp;sig=def"></video>',
            "https://example.com/video-1080.mp4?token=abc&sig=def",
        ),
        (
            '<source src="https://cdn.example.com/vod/clip-720.mp4"></source>',
            "https://cdn.example.com/vod/clip-720.mp4",
        ),
        (
            '<video data-test="x" src="https://cdn.example.com/clip-1.mp4"></video>',
            "https://cdn.example.com/clip-1.mp4",
        ),
        ("<html>No video here</html>", None),
    ],
)
def test_extract_mp4_url_from_html(html_text, expected):
    # Covers: TODO-TEST-CLIPS-EXTRACT
    assert clips.extract_mp4_url_from_html(html_text) == expected


def test_download_clip_from_html(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-DOWNLOAD
    html_text = (
        '<video src="https://cdn.example.com/video-720.mp4?token=abc&amp;sig=def"></video>'
    )

    class _DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return html_text.encode("utf-8")

    def _fake_urlopen(_request, timeout=15):
        return _DummyResponse()

    def _fake_urlretrieve(url, output_path):
        Path(output_path).write_text(url)
        return output_path, None

    monkeypatch.setattr(clips.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(clips.urllib.request, "urlretrieve", _fake_urlretrieve)

    output_path, video_url = clips.download_clip(
        "https://www.twitch.tv/someone/clip/Slug",
        output_dir=str(tmp_path),
    )

    assert Path(output_path).exists()
    assert video_url == "https://cdn.example.com/video-720.mp4?token=abc&sig=def"


def test_getclips_respects_zero_max_clips(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-GETCLIPS
    driver = _DummyDriver(["src-1"])
    captured = {"downloads": 0}
    _patch_getclips_common(monkeypatch)
    monkeypatch.setattr(
        clips.urllib.request,
        "urlretrieve",
        lambda *_args, **_kwargs: captured.__setitem__("downloads", captured["downloads"] + 1),
    )

    clips.getclips(
        "tester",
        current_videos_dir=str(tmp_path),
        max_clips=0,
        wait_seconds=1,
        apply_overlay=False,
        driver=driver,
    )

    assert not list(tmp_path.glob("*.mp4"))
    assert captured["downloads"] == 0
    assert any("/clips?filter=clips&range=24hr" in url for url in driver.visited)


def test_download_clip_uses_direct_mp4_url(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-DOWNLOAD
    captured = {}

    def _fake_urlretrieve(url, output_path):
        captured["url"] = url
        Path(output_path).write_text("ok")
        return output_path, None

    monkeypatch.setattr(clips.urllib.request, "urlretrieve", _fake_urlretrieve)

    output_path, video_url = clips.download_clip(
        "https://cdn.example.com/video-1080.mp4",
        output_dir=str(tmp_path),
    )

    assert video_url == "https://cdn.example.com/video-1080.mp4"
    assert Path(output_path).exists()
    assert captured["url"] == "https://cdn.example.com/video-1080.mp4"


def test_download_clip_raises_when_no_source(monkeypatch, tmp_path):
    # Covers: TODO-TEST-CLIPS-DOWNLOAD
    class _EmptyDriver:
        def get(self, _url):
            return None

        def find_element(self, _by, _selector):
            return _DummyElement(src=None)

    class _SilentWait:
        def until(self, *_args, **_kwargs):
            return None

    def _fake_urlopen(_request, timeout=15):
        class _DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"<html>No video here</html>"

        return _DummyResponse()

    monkeypatch.setattr(clips.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(clips, "WebDriverWait", lambda *_args, **_kwargs: _SilentWait())

    with pytest.raises(ValueError, match="Could not locate clip video source"):
        clips.download_clip(
            "https://www.twitch.tv/someone/clip/Slug",
            output_dir=str(tmp_path),
            driver=_EmptyDriver(),
        )
