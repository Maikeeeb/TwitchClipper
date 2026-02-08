import os
import sys
import urllib.request


def main():
    # Avoid importing this file as the selenium package.
    script_dir = os.path.dirname(__file__)
    if script_dir in sys.path:
        sys.path.remove(script_dir)

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    base_dir = os.path.dirname(__file__)
    gecko_path = os.path.join(base_dir, "geckodriver.exe")
    service = Service(executable_path=gecko_path)

    options = webdriver.FirefoxOptions()
    driver = webdriver.Firefox(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get("https://www.twitch.tv/")

        try:
            consent = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button#L2AGLb"))
            )
            consent.click()
        except Exception:
            pass

        try:
            consent = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"))
            )
            consent.click()
        except Exception:
            pass

        search_box_selector = (
            "input[data-a-target='tw-input'][type='search'][autocomplete='twitch-nav-search']"
        )

        try:
            search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, search_box_selector)))
        except Exception:
            try:
                search_icon = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Search']"))
                )
                search_icon.click()
            except Exception:
                pass
            search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, search_box_selector)))

        search_box.clear()
        search_box.send_keys("zubatlel")
        search_box.send_keys(Keys.ENTER)

        try:
            wait.until(EC.url_contains("/search"))
        except Exception:
            driver.get("https://www.twitch.tv/search?term=zubatlel")
            wait.until(EC.url_contains("/search"))

        result_selectors = [
            "[data-test-selector='search-result-page']",
            "[data-a-target='search-result-card']",
            "[data-test-selector='search-result-card']",
            "div[data-a-target='search-result-section']",
            "div[data-test-selector='search-result-section']",
            "a[data-a-target='preview-card-image-link']",
            "a[data-a-target='preview-card-title-link']",
            "a[href*='zubatlel']",
        ]

        def _has_results(driver_instance):
            return any(driver_instance.find_elements(By.CSS_SELECTOR, sel) for sel in result_selectors)

        wait.until(_has_results)
        print("Search results loaded for Twitch.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
