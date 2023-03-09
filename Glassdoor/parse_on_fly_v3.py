# Do not "clear all"
# Go to url for page instead of clicking next page

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.firefox.webdriver import FirefoxProfile
from selenium.webdriver.support.ui import Select
import time
import os
import math
import pandas as pd
import numpy as np
import glob
from random import randint
from bs4 import BeautifulSoup
import re
from datetime import datetime
from datetime import timedelta
from datetime import date
import sys
import wrangle

##############################################################################
# SET PARSER TYPE HERE: lxml vs html.parser
parsertype = 'html.parser'
sourcedat = 'https://www.glassdoor.com/Reviews/MDC-Holdings-Reviews-E4297172.htm'  # sys.argv[1] # either scraped/sp1500_nreviews.csv or a url
sort = 'oldest_first'  # sys.argv[2] #'newest_first' or 'oldest_first'
##############################################################################

print(sourcedat)

# Change to Your Path
os.chdir(r"C:\Users\zcalv\OneDrive\Desktop\Mannor Lab")  # change this to your path

logfile = 'scraped/exceptions_' + sort + '.log'

if sourcedat.split('.')[-1] in ['htm', 'html']:
    co_todo = pd.DataFrame({'Glassdoor Review Page': [sourcedat],
                            'costub': [sourcedat.split('/')[-1].replace('.html', '').replace('.htm', '')]})

else:
    dat = pd.read_csv(sourcedat)
    dat['costub'] = dat['Glassdoor Review Page'].apply(
        lambda x: str(x).split('/')[-1].replace('.html', '').replace('.htm', ''))

    scrapedcos = [p.lstrip('scraped/' + sort + '/').rstrip('.csv') for p in glob.glob('scraped/' + sort + '/*')]

    scrapedcos = pd.DataFrame({'costub': scrapedcos})

    co_todo0 = wrangle.anti_join(dat, scrapedcos, on='costub')

    co_todo0 = co_todo0.reset_index(drop=True)

    co_todo = co_todo0

print(f'scraping {co_todo.shape[0]} companies')

# HEADLESS FIREFOX
# Change this path to your path
profile = FirefoxProfile(r"C:\Users\zcalv\AppData\Roaming\Mozilla\Firefox\Profiles\brktu7xa.default-1667239152833")
options = Options()
options.headless = True
caps = DesiredCapabilities().FIREFOX
caps["pageLoadStrategy"] = "normal"
browser = webdriver.Firefox(profile,
                            executable_path=r"C:\Users\zcalv\geckodriver-v0.28.0-win64\geckodriver.exe",
                            # Change this to your path
                            options=options,
                            desired_capabilities=caps)

for idx, co in co_todo.iterrows():
    time.sleep(randint(1, 5))
    reviewspage = co['Glassdoor Review Page']
    outfile = 'scraped/' + sort + '/' + co['costub'] + '.csv'

    if os.path.exists(os.getcwd() + '/' + outfile):
        df_reviews_all = pd.read_csv(outfile)
    else:
        df_reviews_all = pd.DataFrame()

    # go straight to reviews page
    if sort == 'newest_first':
        tf = 'false'
    elif sort == 'oldest_first':
        tf = 'true'
    else:
        sys.exit('enter a valid sort parameter')
    reviewspage_sorted = reviewspage + '?sort.sortType=RD&sort.ascending=' + tf

    print(f'{reviewspage_sorted}')

    browser.get(reviewspage_sorted)

    time.sleep(1)

    # get supposed total number of English reviews to iterate over
    try:
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH, '//div[@id="Footer"]')))
    except TimeoutException:
        print(f'landing page did not load')
        browser.execute_script("document.body.style.transform = 'scale(0.9)'")
        browser.save_screenshot("screenshot.png")
        continue

    nreviews_str = \
    browser.find_element_by_xpath('//h2[@data-test="overallReviewCount"]/span').text.split('Found ')[-1].split(' ')[
        0].replace(',', '')

    nreviews = int(nreviews_str)

    niter = math.ceil(nreviews / 10)

    print(f'{reviewspage_sorted}: {nreviews}, {niter}')

    # df_reviews_all = pd.DataFrame()

    time.sleep(randint(5, 10))

    for i in range(niter):
        # skip if page already scraped previously
        if df_reviews_all.shape[0] > 0 and any(df_reviews_all['page'] == (i + 1)):
            continue

        if i == 0:
            # stay on landing page
            pass
        else:
            # load new page
            currenturl = reviewspage_sorted.replace('.htm', '_P' + str(i + 1) + '.htm')

            browser.get(currenturl)

            try:
                WebDriverWait(browser, 30).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="paginationFooter"]')))
            except TimeoutException:
                errmsg = f'{currenturl}: did not load'
                # print(errmsg)
                with open(logfile, 'a') as lf:
                    lf.write(f'{date.today()}: {errmsg}\n')
                continue

        if (round(niter / 10) * 10) / (i + 1) == 2:
            print(f'50% done: {date.today()}, {datetime.now().strftime("%H:%M:%S")}')

        time.sleep(1)

        try:
            WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH, "//div[@id='ReviewsRef']")))
        except TimeoutException:
            errmsg = f'{currenturl}: reviews not reached'
            # print(errmsg)
            with open(logfile, 'a') as lf:
                lf.write(f'{date.today()}: {errmsg}\n')
            continue
        # else:
        #     browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")

        continuereading_xpath = "//div[contains(@class, 'continueReading')]"
        try:
            truncreviews = browser.find_elements_by_xpath(continuereading_xpath)
        except:
            errmsg = f'{currenturl}: Continue Reading xpath is stale'
            # print(errmsg)
            with open(logfile, 'a') as lf:
                lf.write(f'{date.today()}: {errmsg}\n')
            continue

        flag_incomplete = ''
        if len(truncreviews) > 0:
            for trunc in truncreviews:
                try:
                    WebDriverWait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, continuereading_xpath)))
                except TimeoutException:
                    print(f'{currenturl}: timed out waiting for Continue Reading to be clickable')
                else:
                    try:
                        trunc.click()
                    except:
                        flag_incomplete = '1'
                    else:
                        flag_incomplete = '0'
                finally:
                    time.sleep(randint(1, 5))

        html = browser.page_source.encode('utf-8')

        soup = BeautifulSoup(html, parsertype)

        reviews = soup.find('div', {'id': 'ReviewsRef'}).find('div', {'id': 'ReviewsFeed'}).find('ol', {
            'class': 'empReviews'}).find_all('li', {'id': re.compile('empReview')})

        df_reviews = pd.DataFrame()

        for rvw in reviews:
            dct_rvw = dict()

            try:
                ratingnumber = rvw.find('span', {'class': re.compile('ratingNumber')}).text
            except:
                ratingnumber = ''

            dct_hd = dict()
            try:
                hoverdetails = rvw.find('div', {'class': 'tooltipContainer'}).find('div', {'class': 'content'}).find(
                    'ul').find_all('li')
            except:
                pass
            else:
                for det in hoverdetails:
                    key = re.search(r'[a-zA-Z/&\s]*', det.text)[0]
                    val = ''
                    if det.find('div', {'class': 'css-xd4dom'}):
                        val = '1'
                    elif det.find('div', {'class': 'css-18v8tui'}):
                        val = '2'
                    elif det.find('div', {'class': 'css-vl2edp'}):
                        val = '3'
                    elif det.find('div', {'class': 'css-1nuumx7'}):
                        val = '4'
                    elif det.find('div', {'class': 'css-s88v13'}):
                        val = '5'
                    else:  # save the class value and decipher stars later (ie 1.5, 2.5, 3.5...)
                        try:
                            val = det.find('div', {'class': re.compile(r'^css')})['class'][0]
                        except:
                            pass

                    dct_hd[key] = val

            try:
                emptype = rvw.find('span', {'class': re.compile('pt-xsm')}).text
            except:
                emptype = ''

            try:
                rvwtitle0 = rvw.find('h2', {'class': 'mb-xxsm'})
            except:
                pass
            else:
                try:
                    rvwtitle = rvwtitle0.text.strip()
                except:
                    rvwtitle = ''

            try:
                rvwlink = rvwtitle0.find('a')['href']
            except:
                rvwlink = ''

            try:
                empinfo = rvw.find('span', {'class': 'authorInfo'})
            except:
                pass
            else:
                try:
                    rvwdate = re.search(r'^.*20[0-9][0-9]\b', empinfo.text)[0]
                except:
                    rvwdate = ''

                try:
                    empjob = empinfo.find('span', {'class': 'authorJobTitle'}).text.replace(rvwdate, '').strip().strip(
                        '-').strip()
                except:
                    empjob = ''

                try:
                    emploc = empinfo.find('span', {'class': 'authorLocation'}).text.strip()
                except:
                    emploc = ''

            dct_ev = dict()

            try:
                empviews = rvw.find('div', {'class': re.compile('reviewBodyCell')}).find_all('div', {
                    'class': 'align-items-center'})
            except:
                pass
            else:
                for ev in empviews:
                    empviewtype = ev.text
                    empviewval = ''
                    if ev.find('span').find('svg', {'class': 'css-hcqxoa-svg'}):
                        empviewval = 'positive'
                    elif ev.find('span').find('svg', {'class': 'css-1kiw93k-svg'}):
                        empviewval = 'negative'
                    elif ev.find('span').find('svg', {'class': 'css-1h93d4v-svg'}):
                        empviewval = 'neutral'
                    elif ev.find('span').find('svg', {'class': 'css-10xv9lv-svg'}):
                        empviewval = 'blank'
                    dct_ev[empviewtype] = empviewval

            try:
                rvwpros = rvw.find('span', {'data-test': 'pros'}).text.strip()
            except:
                rvwpros = ''

            try:
                rvwcons = rvw.find('span', {'data-test': 'cons'}).text.strip()
            except:
                rvwcons = ''

            try:
                rvwadvm = rvw.find('span', {'data-test': 'advice-management'}).text.strip()
            except:
                rvwadvm = ''

            dct_rvw['page'] = (i + 1)
            dct_rvw['rating_overall'] = ratingnumber
            dct_rvw['rating_components'] = dct_hd
            dct_rvw['employment_status'] = emptype
            dct_rvw['review_title'] = rvwtitle
            dct_rvw['review_link'] = rvwlink
            dct_rvw['review_date'] = rvwdate
            dct_rvw['employee_job'] = empjob
            dct_rvw['employee_loc'] = emploc
            dct_rvw['summary_views'] = dct_ev
            dct_rvw['review_pros'] = rvwpros
            dct_rvw['review_cons'] = rvwcons
            dct_rvw['review_advice_mgmt'] = rvwadvm
            dct_rvw['flag_incomplete'] = flag_incomplete

            df_rvw = pd.json_normalize(dct_rvw)

            df_reviews = pd.concat([df_reviews, df_rvw], ignore_index=True)

        del soup, html
        df_reviews_all = pd.concat([df_reviews_all, df_reviews], ignore_index=True)

        df_reviews_all['supposed_n_reviews'] = nreviews_str

        df_reviews_all['Glassdoor Review Page'] = reviewspage

        df_reviews_all.to_csv(outfile, index=False)

        time.sleep(1)

    if len(df_reviews_all) > 0:
        df_reviews_all = wrangle.order_columns(df_reviews_all, ['Glassdoor Review Page', 'supposed_n_reviews'])
        df_reviews_all.to_csv(outfile, index=False)
    print('pausing before moving on to next company')
    time.sleep(randint(120, 600))

browser.close()