import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import utils as U

class VisualAPI:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(options=chrome_options)

        self.driver.set_window_size(1920, 1080)

    def run(self):
        while True:
            try:
                self.driver.get("http://localhost:9000")
                break
            except Exception as e:
                print(e)
                time.sleep(10)
        IMAGE_DIR = 'Adam/game_image'
        U.f_mkdir(IMAGE_DIR)
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
        print('Visual API Ready')
        while True:
            try:
                screenshot_path = os.path.join(IMAGE_DIR, 'tmp.png')
                self.driver.save_screenshot(screenshot_path)
                time.sleep(10)
            except Exception as e:
                print(e)
                time.sleep(10)

    def stop(self):
        self.driver.quit()


module = VisualAPI()
module.run()
