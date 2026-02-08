import html
import os
import re
import time
import threading
import urllib.request
from urllib.parse import urlparse
from multiprocessing import Process

from moviepy.video.VideoClip import TextClip
from moviepy.video.compositing.CompositeVideoClip import (
    CompositeVideoClip,
    concatenate_videoclips,
)
from moviepy.video.fx.FadeIn import FadeIn
from moviepy.video.fx.FadeOut import FadeOut
from moviepy.video.io.VideoFileClip import VideoFileClip
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def overlay(view_count, name, current_videos_dir):
    """Add a streamer name overlay to the first clip."""
    sanitized_name = name.strip("\n")
    source_path = os.path.join(current_videos_dir, f"{view_count}{sanitized_name}0.mp4")
    output_path = os.path.join(current_videos_dir, f"{view_count}{sanitized_name}0.5.mp4")
    text_clip = (
        TextClip(
            text=sanitized_name,
            font_size=50,
            color="white",
            bg_color="red",
            method="label",
        )
        .with_duration(3)
        .with_effects([FadeOut(0.5), FadeIn(0.5)])
        .with_position((45, 600))
    )
    final_clip = [CompositeVideoClip([VideoFileClip(source_path), text_clip])]

    concatenate_videoclips(final_clip).write_videofile(
        output_path, fps=60, remove_temp=True, threads=12
    )


def getclips(
    name,
    current_videos_dir=None,
    max_clips=10,
    geckodriver_path=None,
    wait_seconds=560,
    apply_overlay=True,
    headless=None,
    driver=None,
    download=True,
):
    """Scrape a streamer's recent clips and download them locally."""
    download_list = []
    current_video_urls = set()
    view_count_first = None
    current_video = None
    base_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(base_dir, os.pardir))
    current_videos_dir = current_videos_dir or os.path.join(repo_root, "currentVideos")
    os.makedirs(current_videos_dir, exist_ok=True)

    env_gecko_path = os.getenv("GECKODRIVER_PATH")
    gecko_path = geckodriver_path or env_gecko_path or os.path.join(base_dir, "geckodriver.exe")
    if gecko_path and os.path.exists(gecko_path):
        service = Service(executable_path=gecko_path)
    else:
        service = Service()
    if driver:
        browser = driver
    else:
        options = webdriver.FirefoxOptions()
        if headless is None:
            headless = os.getenv("HEADLESS", "0") == "1"
        if headless:
            options.add_argument("-headless")
        browser = webdriver.Firefox(service=service, options=options)

    # Go to streamer clips page and collect clip links.
    browser.get(f"https://www.twitch.tv/{name}/clips?filter=clips&range=24hr")

    def _find_clip_links(driver):
        selectors = [
            (By.CSS_SELECTOR, "a[href*='/clip/']"),
            (By.CSS_SELECTOR, "a[data-a-target='preview-card-image-link']"),
            (By.CSS_SELECTOR, "a[data-test-selector*='clips-card']"),
        ]
        for by, selector in selectors:
            elements = driver.find_elements(by, selector)
            hrefs = []
            for elem in elements:
                try:
                    href = elem.get_attribute("href")
                except StaleElementReferenceException:
                    href = None
                if href:
                    hrefs.append(href)
            if hrefs:
                return hrefs
        return []

    WebDriverWait(browser, 10).until(lambda drv: _find_clip_links(drv))

    # finds all the video link elements
    video_links = _find_clip_links(browser)
    print(video_links)
    try:
        for index, link in enumerate(video_links[:max_clips]):
            if link and link.startswith("/"):
                link = f"https://www.twitch.tv{link}"
            browser.get(link)  # goes to the link

            def _get_video_src():
                selectors = [
                    ".video-player__container > video:nth-child(1)",
                    ".video-player__container video",
                    "video",
                ]
                for selector in selectors:
                    try:
                        elem = browser.find_element(By.CSS_SELECTOR, selector)
                        src = elem.get_attribute("src")
                        if src:
                            return src
                    except Exception:
                        continue
                return None

            # Wait until the video MP4 appears.
            WebDriverWait(browser, wait_seconds).until(
                lambda _drv: _get_video_src()
            )
            time.sleep(1)
            attempts = 0
            while attempts < 5:
                current_video = _get_video_src()
                if current_video not in current_video_urls:
                    break
                attempts += 1
                time.sleep(0.5)

            if not current_video or current_video in current_video_urls:
                print("Skipping duplicate or missing video src.")
                continue

            print(current_video)
            current_video_urls.add(current_video)

            # WebDriverWait(browser, 560).until(EC.presence_of_element_located((By.CSS_SELECTOR,
            #  'h2.tw-ellipsis')))
            # videoTitle = browser.find_element_by_css_selector(  # gets the video title
            #   'h2.tw-ellipsis').get_attribute("title")

            try:
                WebDriverWait(browser, wait_seconds).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".tw-stat__value"))
                )
                view_count = browser.find_element(By.CSS_SELECTOR, ".tw-stat__value").text
            except Exception:
                view_count = "0"

            # transtionL.append(threading.Thread(target=oneTransition, args=(videoTitle,
            # viewCount + name.strip('\n') + '1')))
            # transtionL[-1].start()  # takes the video title and makes a shit transition
            print(current_video)
            # File naming convention: <viewcount><streamer>0.mp4 (used by oneVideo.py parsing).
            output_path = os.path.join(
                current_videos_dir, view_count + name.strip("\n") + "0" + ".mp4"
            )
            if download:
                download_list.append(
                    threading.Thread(
                        target=urllib.request.urlretrieve, args=(current_video, output_path)
                    )
                )
                print(output_path)
            if index == 0:
                view_count_first = view_count

            if download:
                while True:
                    try:
                        download_list[-1].start()
                        break
                    except ValueError:
                        print("Failed to grab url")
                        current_video = _get_video_src()
                    except Exception as e:
                        print(e)
    finally:
        if driver is None:
            browser.quit()
    if download:
        for video in download_list:
            try:
                video.join()
            except Exception as e:
                print(e)

    if download and view_count_first and apply_overlay:
        overlay_process = Process(
            target=overlay, args=(view_count_first, name, current_videos_dir)
        )
        overlay_process.start()
        overlay_process.join()
        os.remove(
            os.path.join(
                current_videos_dir, view_count_first + name.strip("\n") + "0" + ".mp4"
            )
        )

    return video_links


def extract_mp4_url_from_html(html_text):
    """Extract the first MP4 URL from a Twitch clip HTML response."""
    if not html_text:
        return None
    unescaped = html.unescape(html_text)
    pattern = re.compile(r"""<(?:video|source)[^>]+src=["']([^"']+\.mp4[^"']*)["']""")
    match = pattern.search(unescaped)
    return match.group(1) if match else None


def _build_firefox_driver(headless=None, geckodriver_path=None):
    base_dir = os.path.dirname(__file__)
    env_gecko_path = os.getenv("GECKODRIVER_PATH")
    gecko_path = geckodriver_path or env_gecko_path or os.path.join(base_dir, "geckodriver.exe")
    if gecko_path and os.path.exists(gecko_path):
        service = Service(executable_path=gecko_path)
    else:
        service = Service()

    options = webdriver.FirefoxOptions()
    if headless is None:
        headless = os.getenv("HEADLESS", "0") == "1"
    if headless:
        options.add_argument("-headless")
    return webdriver.Firefox(service=service, options=options)


def download_clip(
    clip_url,
    output_dir=None,
    filename=None,
    driver=None,
    headless=None,
    wait_seconds=30,
    geckodriver_path=None,
):
    """Download a Twitch clip by URL and return (output_path, video_url)."""
    base_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(base_dir, os.pardir))
    output_dir = output_dir or os.path.join(repo_root, "currentVideos")
    os.makedirs(output_dir, exist_ok=True)

    video_url = None
    if ".mp4" in clip_url:
        video_url = clip_url
    else:
        try:
            request = urllib.request.Request(
                clip_url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                html_text = response.read().decode("utf-8", errors="ignore")
            video_url = extract_mp4_url_from_html(html_text)
        except Exception:
            video_url = None

    if not video_url:
        owns_driver = driver is None
        if owns_driver:
            driver = _build_firefox_driver(headless=headless, geckodriver_path=geckodriver_path)
        try:
            driver.get(clip_url)

            def _get_video_src():
                selectors = [
                    ".video-player__container > video:nth-child(1)",
                    ".video-player__container video",
                    "video",
                    "source",
                ]
                for selector in selectors:
                    try:
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        src = elem.get_attribute("src")
                        if src and ".mp4" in src:
                            return src
                    except Exception:
                        continue
                return None

            WebDriverWait(driver, wait_seconds).until(lambda _drv: _get_video_src())
            video_url = _get_video_src()
        finally:
            if owns_driver:
                driver.quit()

    if not video_url:
        raise ValueError("Could not locate clip video source.")

    parsed_video = urlparse(video_url)
    parsed_clip = urlparse(clip_url)
    if filename:
        output_name = filename
    else:
        video_basename = os.path.basename(parsed_video.path)
        if video_basename:
            output_name = video_basename
        else:
            clip_slug = parsed_clip.path.rstrip("/").split("/")[-1] or "clip"
            output_name = f"{clip_slug}.mp4"
    if not output_name.endswith(".mp4"):
        output_name = f"{output_name}.mp4"
    output_path = os.path.join(output_dir, output_name)

    urllib.request.urlretrieve(video_url, output_path)
    return output_path, video_url

    """ # returns the time in a list of [hours, minutes] from where the clip is in the vod
     placeInVod = \
         browser.find_element_by_css_selector('a.tw-align-middle').get_attribute('href').split("t=")[2].split('m')[
             0].split('h')"""


if __name__ == '__main__':
    start_time = time.time()
    getclips("zubatlel")
    print("--- %s seconds ---" % (time.time() - start_time))
