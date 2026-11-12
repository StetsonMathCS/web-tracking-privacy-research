"""import time
from selenium import webdriver
from fingerprint_analyzer import (
    install_fingerprinting_monitor,
    collect_fingerprinting_indicators,
)

driver = webdriver.Chrome()

try:
    installed = install_fingerprinting_monitor(driver);
    print("Monitor installed:", installed)

    driver.get("https://example.com")
    time.sleep(3)

    driver.execute_script("""
     # const canvas = document.createElement("canvas");
      #canvas.width = 100;
      #canvas.height = 100;
     #canvas.toDataURL() ;
      #  """)

"""  
    results = collect_fingerprinting_indicators(driver)

    for key, value in results.items():
        print(f"{key}: {value}")

finally:
    driver.quit()

"""
