import pandas as pd
from selenium import webdriver

#load the dataset
websites = pd.read_excel("data/Website_Testing.xlsx")

#select the first website to test
url = websites.loc[0, "URL"]
#start the selenium webdriver
driver = webdriver.Chrome()

try:
    #visit the website
    driver.set_page_load_timeout(30)
    driver.get(url)

    #dispplay results
    print("Website URL:", url)
    print("Page Title:", driver.title)
    print("Current URL:", driver.current_url)

    #Count accessible cookies
    cookies = driver.get_cookies()
    print("Number of cookies:", len(cookies))

    for cookie in cookies:
            print(
                    "Name:", cookie["name"],
                    "|Secure:", cookie.get("secure"),
                    "|HttpOnly:", cookie.get("httpOnly"),
                    "|SameSite:", cookie.get("sameSite"),
                
            )
finally:
            driver.quit()
            