# my_utils.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


def get_browser():
    """这是一个获取浏览器的工具函数"""
    options = Options()
    # 这里的路径写死在你的工具文件里就行，不用每次都看
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    service = Service(r"E:\PythonProject2\.venv\Scripts\chromedriver-win64\chromedriver.exe")

    # 返回创建好的浏览器对象
    return webdriver.Chrome(service=service, options=options)
