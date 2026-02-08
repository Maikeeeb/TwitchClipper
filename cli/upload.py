from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from datetime import date


def upload(name):
    firefox_options = webdriver.FirefoxOptions()
    firefox_options.add_argument("--private")

    browser = webdriver.Firefox(options=firefox_options)

    # open webpage and login
    browser.get('https://studio.youtube.com/channel/UCIMcGyIDrKgYfIPzGm79HFQ')
    browser.find_element_by_css_selector('#identifierId').send_keys('autocompilations@gmail.com')
    browser.find_element_by_css_selector('#identifierNext').click()
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.I0VJ4d > div:nth-child(1) > input:nth-child(1)')))
    browser.find_element_by_css_selector('.I0VJ4d > div:nth-child(1) > input:nth-child(1)').send_keys("Awesomenauts1")
    browser.find_element_by_css_selector('#passwordNext').click()

    # open upload page
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#create-icon')))
    browser.find_element_by_css_selector('#create-icon').click()
    browser.find_element_by_css_selector('#text-item-0').click()

    # uploads based off location
    elem = browser.find_element_by_xpath("//input[@type='file']")
    elem.send_keys(
        "C:\\Users\\leagu\\PycharmProjects\\Selenium\\clip montage maker\\fullVideos\\%s.mp4" % 'offlinetv' + str(
            date.today()))
