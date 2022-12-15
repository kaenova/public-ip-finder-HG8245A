import re
import requests
import os

from time import sleep
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By

class Bot:
    __driver: webdriver.Chrome
    __username: str
    __password: str
    __router_ip: str
    __internet_wan_name: str
    
    current_ip = None
    
    def __init__(self, driver_path, chrome_path, router_ip, username, password, internet_wan_name) -> None:
        print("Init bot")
        self.__username = username
        self.__password = password
        self.__router_ip = router_ip
        self.__internet_wan_name = internet_wan_name
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.binary_location = chrome_path

        self.__driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
    
    @staticmethod
    def log(name:str, log):
        now = datetime.now()
        current_time = now.strftime("%d/%m//%Y, %H:%M:%S")
        print(f"[{current_time}][{name}] {log}")
        
    def run(self):
        while True:
            Bot.log("INFO", f"Last detected IP: {self.current_ip}")
            if self.check_modem_alive():
                self.login()
                try:
                    self.check_current_ip()
                    Bot.log("INFO", f"Detected IP: {self.current_ip}")
                    if self.is_restart(self.current_ip):
                        self.restart()
                    else:
                        self.__driver.switch_to.default_content()
                        self.logout()
                except Exception as e:
                    print(f"Exception: {e}")
            Bot.log("INFO", f"Will Check agian in 20 seconds")
            sleep(20)
                
    def check_modem_alive(self) -> bool:
        Bot.log("MODEM_CHECK", f"Checking modem")
        try:
            requests.get(f'{self.__router_ip}', verify=False, timeout=5)
            Bot.log("MODEM_CHECK", f"Alive")
            return True
        except:
            Bot.log("MODEM_CHECK", f"Dead")
            self.current_ip = None
            return False

    def screenshot(self, filename: str):
        self.__driver.save_screenshot(filename)
    
    def is_restart(self, ip) -> bool:
        if ip == None: return False
        match_obj = re.findall("^10.", ip)
        return len(match_obj) != 0
    
    def restart(self):
        self.__driver.switch_to.default_content()
       
        # Move to system tools
        header_nav = self.__driver.find_element(By.ID, "headerTab")
        li_elms = header_nav.find_elements(By.TAG_NAME, "li")
        li_elms[10].click()
        sleep(2)
        # Press reboot button
        iframe_content = self.__driver.find_element(By.ID, "frameContent")
        self.__driver.switch_to.frame(iframe_content)
        self.__driver.find_element(By.ID, "btnReboot").click()
        alert = Alert(self.__driver)
        Bot.log("RESTART", f"Restarting modem")
        alert.accept()
        self.__driver.switch_to.default_content()
        # Set current state
        self.current_ip = None
        
    def login(self):
        self.__driver.get(self.__router_ip)
        sleep(1)
        if self.__driver.current_url != f"{self.__router_ip}/":
            raise Exception(f"Not in login page (current url : {self.__driver.current_url})")
        username = self.__driver.find_element(By.ID, "txt_Username")
        username.send_keys(self.__username)
        password = self.__driver.find_element(By.ID, "txt_Password")
        password.send_keys(self.__password)
        self.__driver.find_element(By.ID, "button").click()
        sleep(3)
        if self.__driver.current_url == f"{self.__router_ip}/index.asp":
            Bot.log("Login", f"Success")
        else:
            Bot.log("Login", f"Failed")
            raise Exception("Login Failed")
    
    def logout(self):
        if (self.__driver.current_url == f"{self.__router_ip}/"):
            Bot.log("Logout", f"Already logged out")
            return
        logout_button = self.__driver.find_elements(By.ID, "headerLogoutText")
        if len(logout_button) < 1:
            raise Exception("Cannot found logout button element")
        logout_button[0].click()
        sleep(3)
    
    def check_current_ip(self):
        # Move to wan nav
        nav_bar = self.__driver.find_element(By.ID, "nav")
        nav_element = nav_bar.find_elements(By.TAG_NAME, "li")
        wan_nav = None
        for elm in nav_element:
            if elm.get_property("value") == 0:
                wan_nav = elm
                break
        if wan_nav == None:
            raise Exception("Nav not found")
        wan_nav.click()
        sleep(3)
        
        # Check table on wan nav
        iframe_content = self.__driver.find_element(By.ID, "frameContent")
        self.__driver.switch_to.frame(iframe_content)
        try:
            ip_div = self.__driver.find_elements(By.ID, "IPv4Panel")
            if len(ip_div) == 0: raise Exception("Table not found")
            ip_table =  ip_div[0]
            table_rows = ip_table.find_elements(By.TAG_NAME, "tr")
            for row in table_rows:
                row_id = row.get_attribute("id")
                if (row_id == None or row_id.strip() == ""):
                    continue
                data = row.find_elements(By.TAG_NAME, "td")
                if data[0].text == self.__internet_wan_name:
                    # Assign current IP
                    self.current_ip = None if data[3].text == "--" else data[3].text
        except:
            pass
        self.__driver.switch_to.default_content()

def get_env(env_name:str, default: str)->str:
    env_val = os.getenv(env_name)
    if env_val == None:
        return default
    return env_val

if __name__ == "__main__":
    print("Loading environment")
    load_dotenv()
    chrome_driver_path = get_env("CHROME_DRIVER_PATH", "./driver/chromedriver.exe")
    chrome_path = get_env("CHROME_PATH", "C:\Program Files\Google\Chrome\Application\chrome.exe")
    router_ip = get_env("ROUTER_IP", "http://192.168.100.1")
    username = get_env("ADMIN_USERNAME", "telecomadmin")
    password = get_env("ADMIN_PASSWORD", "admintelecom")
    wan = get_env("WAN_NAME", "2_INTERNET_R_VID_200")
    
    agent = Bot(chrome_driver_path, chrome_path, router_ip, username, password, wan)
    agent.run()