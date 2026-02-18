import pytest
import os
import json
from unittest import mock
from backend.vod_download import download_vod, VodAsset


def test_local_path_copies_and_writes_json(tmp_path):
    """Copy local mp4 file and write metadata JSON."""
    local_mp4 = tmp_path / "test.mp4"
    local_mp4.write_bytes(b"fake video content")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    vod_asset = download_vod(str(local_mp4), output_dir=str(output_dir))

    assert (output_dir / "vod.mp4").exists()
    assert (output_dir / "vod.json").exists()
    assert vod_asset.vod_path == str(output_dir / "vod.mp4")
    assert vod_asset.metadata_path == str(output_dir / "vod.json")


def test_twitch_url_calls_ytdlp_subprocess_mocked(tmp_path):
    """Twitch URL triggers yt-dlp subprocess calls for metadata and download."""
    mock_metadata = {
        'title': 'Test VOD',
        'uploader': 'TestStreamer',
        'duration': 3600,
        'view_count': 1000,
    }

    with mock.patch('backend.vod_download.subprocess.run') as mock_run:
        # First call returns metadata JSON, second call downloads video
        mock_result = mock.Mock()
        mock_result.stdout = json.dumps(mock_metadata)
        mock_run.return_value = mock_result

        # Create the output file so VodAsset can be returned
        output_mp4 = tmp_path / "vod.mp4"
        output_mp4.write_bytes(b"fake video")

        vod_asset = download_vod(
            'https://www.twitch.tv/videos/1234567890',
            output_dir=str(tmp_path),
        )

        # Verify subprocess was called twice (metadata + download)
        assert mock_run.call_count == 2
        
        # Check first call is for metadata extraction
        first_call_args = mock_run.call_args_list[0][0][0]
        assert first_call_args[0] == 'yt-dlp'
        assert '--dump-json' in first_call_args
        assert 'https://www.twitch.tv/videos/1234567890' in first_call_args
        
        # Check second call is for download with format selection
        second_call_args = mock_run.call_args_list[1][0][0]
        assert second_call_args[0] == 'yt-dlp'
        assert '-f' in second_call_args  # Format arg present
        assert 'best[height<=' in second_call_args[second_call_args.index('-f') + 1]

        # Verify metadata was written with extracted values
        assert (tmp_path / "vod.json").exists()
        with open(tmp_path / "vod.json") as f:
            metadata = json.load(f)
            assert metadata['title'] == 'Test VOD'
            assert metadata['uploader'] == 'TestStreamer'
            assert metadata['duration_s'] == 3600
            assert metadata['views'] == 1000


def test_twitch_url_missing_ytdlp_gives_clear_error(tmp_path):
    """Missing yt-dlp raises RuntimeError with clear message."""
    with mock.patch(
        'backend.vod_download.subprocess.run', side_effect=FileNotFoundError
    ):
        with pytest.raises(RuntimeError, match="yt-dlp is not installed"):
            download_vod(
                'https://www.twitch.tv/videos/1234567890', output_dir=str(tmp_path)
            )


def test_invalid_input_raises_value_error():
    """Invalid input string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid input string:"):
        download_vod('invalid_url')


def test_direct_mp4_url_downloads(tmp_path):
    """Direct MP4 URL downloads successfully."""
    mock_content = b"fake mp4 content"

    with mock.patch('requests.get') as mock_get:
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.content = mock_content
        mock_get.return_value = mock_response

        vod_asset = download_vod(
            'http://example.com/video.mp4', output_dir=str(tmp_path)
        )

        assert (tmp_path / "vod.mp4").exists()
        assert (tmp_path / "vod.json").exists()
        assert (tmp_path / "vod.mp4").read_bytes() == mock_content


def test_direct_mp4_url_failure(tmp_path):
    """Direct MP4 URL failure raises RuntimeError."""
    with mock.patch('requests.get') as mock_get:
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to download"):
            download_vod('http://example.com/missing.mp4', output_dir=str(tmp_path))


def test_local_file_copies_content(tmp_path):
    """Local file content is copied correctly."""
    local_mp4 = tmp_path / "source.mp4"
    content = b"original mp4 content"
    local_mp4.write_bytes(content)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    download_vod(str(local_mp4), output_dir=str(output_dir))

    assert (output_dir / "vod.mp4").read_bytes() == content


def test_metadata_json_structure(tmp_path):
    """Metadata JSON has required structure."""
    local_mp4 = tmp_path / "test.mp4"
    local_mp4.write_bytes(b"fake video")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    download_vod(str(local_mp4), output_dir=str(output_dir))

    with open(output_dir / "vod.json") as f:
        metadata = json.load(f)

    assert 'source_url' in metadata
    assert 'downloaded_at' in metadata
    assert 'output_mp4' in metadata
    assert 'title' in metadata
    assert 'uploader' in metadata
    assert 'duration_s' in metadata
    assert 'extractor' in metadata
    assert metadata['title'] is None
    assert metadata['uploader'] is None
    assert metadata['duration_s'] is None
