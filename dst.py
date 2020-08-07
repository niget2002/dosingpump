""" dst.py : calculates time based on current dst """

import time

def dst_time():
    year = time.localtime()[0] #get current year

    hh_march = time.mktime((year, 3, (14-(int(5*year/4+1))%7), 1, 0, 0, 0, 0, 0)) #Time of March change to DST
    hh_november = time.mktime((year, 10, (7-(int(5*year/4+1))%7), 1, 0, 0, 0, 0, 0)) #Time of October change to EST

    now = time.time()
    if now < hh_march: # we are before last sunday of march
        dst = time.localtime(now-21600) # EST: UTC-5H
    elif now < hh_november: # we are before last sunday of october
        dst = time.localtime(now-18000) # DST: UTC-4H
    else: # we are after last sunday of october
        dst = time.localtime(now-21600) # EST: UTC-5H

    return dst
