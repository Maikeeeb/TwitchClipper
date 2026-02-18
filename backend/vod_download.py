import json
import os
import subprocess
from datetime import datetime, timezone


class VodAsset:
    """Represents downloaded VOD with metadata and paths."""

    def __init__(
        self,
        vod_path,
        metadata_path,
        chat_path=None,
        montage_path=None,
        segments=None,
    ):
        self.vod_path = vod_path
        self.metadata_path = metadata_path
        self.chat_path = chat_path
        self.montage_path = montage_path
        self.segments = segments or []


def _download_local_file(local_path: str, output_mp4: str) -> None:
    """Copy a local mp4 file to the output directory."""
    with open(local_path, 'rb') as fsrc, open(output_mp4, 'wb') as fdst:
        fdst.write(fsrc.read())


def _download_direct_url(vod_url: str, output_mp4: str) -> None:
    """Download mp4 from a direct URL."""
    try:
        import requests
    except ImportError:
        raise RuntimeError(
            "requests library is not installed. "
            "Install it to download from direct URLs."
        )

    response = requests.get(vod_url)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to download from {vod_url}: {response.status_code}")

    with open(output_mp4, 'wb') as f:
        f.write(response.content)


def _download_twitch_vod(vod_url: str, output_mp4: str, quality: str = "480p") -> dict:
    """Download Twitch VOD using yt-dlp and extract metadata.
    
    Note: This makes two subprocess calls (metadata extraction + download).
    Future optimization: could combine into single call with metadata output.
    """
    try:
        # First, get metadata using --dump-json
        result = subprocess.run(
            ['yt-dlp', '--dump-json', vod_url],
            capture_output=True,
            text=True,
            check=True,
        )
        metadata = json.loads(result.stdout)
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp is not installed. "
            "Please install it to download Twitch VODs."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get metadata from {vod_url}: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse metadata from {vod_url}: {e}")

    # Now download the video with quality filter
    try:
        format_str = f"best[height<={quality.replace('p', '')}]"
        
        subprocess.run(
            ['yt-dlp', '-f', format_str, '-o', output_mp4, vod_url],
            check=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "yt-dlp is not installed. "
            "Please install it to download Twitch VODs."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to download VOD from {vod_url}: {e}")

    return metadata

    return metadata


def _write_metadata(
    vod_url: str,
    output_mp4: str,
    metadata_path: str,
    is_twitch: bool,
    extracted_metadata: dict = None,
) -> None:
    """Write metadata JSON file."""
    now = datetime.now(timezone.utc).isoformat()

    metadata = {
        'source_url': vod_url,
        'downloaded_at': now,
        'output_mp4': output_mp4,
        'title': None,
        'uploader': None,
        'duration_s': None,
        'game': None,
        'views': None,
        'extractor': 'yt-dlp' if is_twitch else None,
    }

    # Populate from extracted metadata if available
    if extracted_metadata:
        metadata['title'] = extracted_metadata.get('title')
        metadata['uploader'] = extracted_metadata.get('uploader')
        metadata['duration_s'] = extracted_metadata.get('duration')
        metadata['game'] = extracted_metadata.get('category')
        # Views are in statistics or view_count
        views = extracted_metadata.get('view_count') or extracted_metadata.get(
            'statistics', {}
        ).get('views')
        metadata['views'] = views

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)


def download_vod(vod_url: str, *, output_dir: str = ".", quality: str = "480p") -> VodAsset:
    """
    Download a VOD from various sources.

    Supports:
    - Twitch VOD page URL (https://www.twitch.tv/videos/<id>)
    - Direct MP4 URL (http/https)
    - Local mp4 file path

    Args:
        vod_url: URL or local path to download from
        output_dir: Directory to save vod.mp4 and vod.json
        quality: Video quality for Twitch VODs (default "480p")

    Returns:
        VodAsset with paths to downloaded mp4 and metadata JSON

    Raises:
        ValueError: If vod_url format is invalid
        RuntimeError: If download fails or dependencies missing
    """
    os.makedirs(output_dir, exist_ok=True)

    output_mp4 = os.path.join(output_dir, 'vod.mp4')
    metadata_path = os.path.join(output_dir, 'vod.json')

    # Case A: Local file path
    if vod_url.endswith('.mp4') and os.path.isfile(vod_url):
        _download_local_file(vod_url, output_mp4)
        _write_metadata(vod_url, output_mp4, metadata_path, is_twitch=False)
    # Case C: Twitch VOD page URL
    elif 'twitch.tv/videos/' in vod_url:
        extracted_metadata = _download_twitch_vod(vod_url, output_mp4, quality=quality)
        _write_metadata(
            vod_url,
            output_mp4,
            metadata_path,
            is_twitch=True,
            extracted_metadata=extracted_metadata,
        )
    # Case B: Direct mp4 URL
    elif vod_url.startswith('http') and vod_url.endswith('.mp4'):
        _download_direct_url(vod_url, output_mp4)
        _write_metadata(vod_url, output_mp4, metadata_path, is_twitch=False)
    else:
        raise ValueError(f"Invalid input string: {vod_url}")

    return VodAsset(vod_path=output_mp4, metadata_path=metadata_path)
