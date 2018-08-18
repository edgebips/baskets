#!/usr/bin/env python3
"""Download holdings from Vanguard.
"""

symbol = 'VNQ'
url = "https://advisors.vanguard.com/web/c1/fas-investmentproducts/{symbol}/portfolio".format(symbol=symbol)

import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import os
#os.environ['PATH'] = os.getenv('PATH') + ':/usr/lib/chromium-browser'
#os.environ['PATH'] = os.getenv('PATH') + ':/home/blais/src/geckodriver-v0.21.0-linux64'
#os.environ['PATH'] = os.getenv('PATH') + ':/home/blais/src'

from selenium.webdriver.chrome import options

prefs = {"download.default_directory" : "/tmp/dl"}

# chromeOptions = webdriver.ChromeOptions()
# chromeOptions.add_experimental_option("prefs", prefs)
# chromedriver = "path/to/chromedriver.exe"
# driver = webdriver.Chrome(executable_path=chromedriver, chrome_options=chromeOptions)


opts = options.Options()
opts.add_experimental_option("prefs", prefs)
#opts.set_headless(True)
print(opts.to_capabilities())

driver = webdriver.Chrome(executable_path="/home/blais/src/chromedriver", options=opts)

#driver.set_headless(True)
driver.get(url)
print(driver.title)
time.sleep(3)

element = driver.find_element_by_link_text("Holding details")
print(element)
element.click()

element = driver.find_element_by_link_text("Export data")
print(element)
element.click()

#time.sleep(100)

# elem = driver.find_element_by_name("q")
# elem.clear()
# elem.send_keys("pycon")
# elem.send_keys(Keys.RETURN)
# assert "No results found." not in driver.page_source

print('closing')
driver.close()
print('closed')



# import mechanicalsoup
# browser = mechanicalsoup.StatefulBrowser()
# browser.open(url)
# print(browser.get_current_page())
# #browser.follow_link("Export")


#print(x)




# import re
# import mechanize

# symbol = 'VNQ'

# br = mechanize.Browser()
# br.open("https://advisors.vanguard.com/web/c1/fas-investmentproducts/{symbol}/portfolio".format(symbol))
# # follow second link with element text matching regular expression
# response1 = br.follow_link(text_regex=r"cheese\s*shop", nr=1)
# print(br.title())
# print(response1.geturl())
# print(response1.info())  # headers
# print(response1.read())  # body

# br.select_form(name="order")
# # Browser passes through unknown attributes (including methods)
# # to the selected HTMLForm.
# br["cheeses"] = ["mozzarella", "caerphilly"]  # (the method here is __setitem__)
# # Submit current form.  Browser calls .close() on the current response on
# # navigation, so this closes response1
# response2 = br.submit()

# # print currently selected form (don't call .submit() on this, use br.submit())
# print(br.form)

# response3 = br.back()  # back to cheese shop (same data as response1)
# # the history mechanism returns cached response objects
# # we can still use the response, even though it was .close()d
# response3.get_data()  # like .seek(0) followed by .read()
# response4 = br.reload()  # fetches from server

# for form in br.forms():
#     print(form)
# # .links() optionally accepts the keyword args of .follow_/.find_link()
# for link in br.links(url_regex="python.org"):
#     print(link)
#     br.follow_link(link)  # takes EITHER Link instance OR keyword args
#     br.back()



# # import argparse
# # import logging
# # from urllib.parse import unquote


# # def main():
# #     logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
# #     parser = argparse.ArgumentParser(description=__doc__.strip())
# #     #parser.add_argument('filenames', nargs='+', help='Filenames')
# #     args = parser.parse_args()

# #     # ...
# #     x = unquote('https%3A%2F%2Fadvisors.vanguard.com%2Fweb%2Fc1%2Ffas-investmentproducts%2F0970%2Fportfolio%23&c.&peRelationship=Crossover&fileDownloaded=1&downloadName=csv%3AHolding_details_Total_Stock_Market_ETF_%28VTI%29&downloadLocation=us%3Aen%3Afas%3Aweb%3Aadvisors%3Ainvproducts%3Aportfolio%3A0970&pageName=us%3Aen%3Afas%3Aweb%3Aadvisors%3Ainvproducts%3Aportfolio%3A0970&.c&cc=USD&s=2560x1440&c=24&j=1.6&v=N&k=Y&bw=1787&bh=1352&AQE=1')
# #     print(x)


# # if __name__ == '__main__':
# #     main()


# # 'https://vanguard.d2.sc.omtrdc.net/b/ss/vanguardfaslaunch/1/JS-1.8.0/s22966595702971?AQB=1&ndh=1&pf=1&t=17%2F7%2F2018%202%3A1%3A34%205%20240&mid=06472755307644493300559037431780657247&aid=2D72A7D00530B7C4-60000300803C193C&aamlh=7&ce=ISO-8859-1&ns=vanguard&cdp=2&pageName=us%3Aen%3Afas%3Aweb%3Aadvisors%3Ainvproducts%3Aportfolio%3A0970&g=https%3A%2F%2Fadvisors.vanguard.com%2Fweb%2Fc1%2Ffas-investmentproducts%2F0970%2Fportfolio%23&c.&peRelationship=Crossover&fileDownloaded=1&downloadName=csv%3AHolding_details_Total_Stock_Market_ETF_%28VTI%29&downloadLocation=us%3Aen%3Afas%3Aweb%3Aadvisors%3Ainvproducts%3Aportfolio%3A0970&pageName=us%3Aen%3Afas%3Aweb%3Aadvisors%3Ainvproducts%3Aportfolio%3A0970&.c&cc=USD&s=2560x1440&c=24&j=1.6&v=N&k=Y&bw=1787&bh=1352&AQE=1'
