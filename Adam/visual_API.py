import os
import time
from selenium import webdriver
import utils as U

class VisualAPI:
    def __init__(self):
        self.driver = webdriver.Chrome()

        self.driver.set_window_size(320, 512)

    def run(self):
        self.driver.get("http://localhost:9000")
        IMAGE_DIR = 'Adam/game_image'
        U.f_mkdir(IMAGE_DIR)
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)
        print('Visual API Ready')
        while True:
            screenshot_path = os.path.join(IMAGE_DIR, 'tmp.png')
            self.driver.save_screenshot(screenshot_path)
            time.sleep(10)

    def stop(self):
        self.driver.quit()


module = VisualAPI()
module.run()
