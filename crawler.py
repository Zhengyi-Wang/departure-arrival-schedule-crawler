from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

import numpy as np
import pandas as pd
import re
import datetime
import pytz
import time


class DepArrCrawler(object):
    def __init__(self, airport, mode):
        self.airport = airport
        self.mode = mode


    def isElementExist(self, element):
            flag=True
            driver=self.driver
            try:
                driver.find_element_by_xpath(element)
                return flag
            except:
                flag=False
                return flag

    def from12hto24h(self, raw_t):
        t, flag = raw_t.split(' ')
        h, m = t.split(':')
        h, m = int(h), int(m)
        if flag == 'PM' and h != 12:
            return str(h+12) + ':' + str(m)
        elif flag == 'AM' and h == 12:
            return str(h-12) + ':' + str(m)
        else:
            return str(h) + ':' + str(m)

    def driverSelenium(self):
        driver = webdriver.Firefox()
        # Driver action
        try:
            driver.get("https://www.flightradar24.com/data/airports/" + self.airport + "/" + self.mode + "#")
        except Exception as e:
            print(e)
        time.sleep(20)

        while True:
            try:
        #         driver.execute_script("document.getElementsByClassName('btn btn-table-action btn-flights-load')[0].click()")
        #         driver.execute_script("document.getElementsByClassName('btn btn-table-action btn-flights-load')[1].click()")
        #         driver.find_element_by_css_selector("[ng-click='loadMoreFlights($event)']").click()
                driver.find_element_by_css_selector("[data-loading-text='<i class=\"fa fa-circle-o-notch fa-spin\"></i> Loading later flights...']").click()
                time.sleep(np.random.random())
            except Exception as e:
                print(e)
                break    
        # Get html
        html = driver.page_source
        
        #driver.get_screenshot_as_file("screenshot.png")
        driver.close()
        return html

    def htmlParser(self, html):
        week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
        'Saturday', 'Sunday']
        soup = BeautifulSoup(html, "html.parser")
        trs = soup.find_all(name = 'tr')

        len_trs = len(trs[4:-2])
        df = pd.DataFrame(index = np.arange(0, len_trs+1), 
                              columns=['Status', 'Time_Status', 'Time_Estimated',
                                       'Flight', 'Codeshare', 'Aircraft_Registration',
                                       'Aircraft_Type', 'Aircraft_Type_Complete',
                                       'From_Airport', 'Airline'])
        for num, tr in enumerate(trs[4:-2]):   
            # Extract date info
            if tr.text.split(',')[0] in week:
                df.iloc[num+1, 0] = tr.text
                df.iloc[num] = df.iloc[num].fillna('')
                continue

            # Status
            status = re.findall('objFlight.flight.statusMessage.text \| unsafe">.*',
                                str(tr))[0].split('>')[1].split('<')[0] 
            # Time_Status
            time_status = re.findall('objFlight.flight.statusMessage.text \| unsafe">.*',
                                     str(tr))[0].split('> ')[1].split('<')[0]
            # Time_Estimated
            time_estimated = re.findall('class="ng-binding">\d+:\d+\s\w+', str(tr))[0].split('>')[1]
            if len(time_status) != 0:
                time_status = self.from12hto24h(time_status)
            if len(time_estimated) != 0:
                time_estimated = self.from12hto24h(time_estimated)

            # Flight
            flight = tr.find(href = re.compile("flights")).text

            # Codeshare
            codeshare = ''
            codeshare_string = tr.find_all('a', {'class': "chevron-toggle ng-scope"})
            if len(codeshare_string) != 0:
                for link in codeshare_string:
                    codeshare = link.get('data-codeshare')[1:-1]

            # Aircraft Registration
            aircraftReg = tr.find(attrs={"ng-show": "(objFlight.flight.aircraft.registration)"}).text
            if '(' in aircraftReg:
                aircraftReg = aircraftReg[1:-2]
            aircraftType_string = tr.find(attrs={"class": re.compile("p-xxs ng-binding"),
                                       "title": re.compile(".*")})
            if aircraftType_string is not None:
                aircraftType_complete = aircraftType_string['title']
                aircraftType = aircraftType_string.text[1:]
            else:
                aircraftType_complete = ''
                aircraftType = tr.find(attrs={"ng-show": "(objFlight.flight.aircraft.model.code)"}).text[:-1]
            if '(' in aircraftType:
                aircraftType = aircraftType[1:-1]
            from_airport = tr.find(href = re.compile("airport")).text[1:-1]
            airline = tr.find(attrs={"ng-show": "(objFlight.flight.airline.name)"}).text 

            df.iloc[num+1] = [status, time_status, time_estimated, flight, codeshare,
                       aircraftReg, aircraftType, aircraftType_complete, from_airport,
                       airline]
        return df, trs

    def saveFile(self, df, trs):
        base_UTC = re.search('\d+\.\d+', str(trs[1])).group(0)
        base_time = datetime.datetime.fromtimestamp(round(float(base_UTC)), pytz.timezone('Europe/Paris')).strftime('%Y-%m-%d_%H-%M')
        filename = self.mode + "_" + self.airport + "_" + base_time + ".csv"
        with open(filename, 'a') as f:   
            df.to_csv(f)
            
    def crawler(self):
        html = self.driverSelenium()
        df, trs = self.htmlParser(html)
        self.saveFile(df, trs)
    
if __name__ == '__main__':
    cdgArr = DepArrCrawler('cdg', 'arrivals')
    cdgArr.crawler()
