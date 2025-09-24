#!/usr/bin/python
# -*- coding: utf-8 -*-

# Mats Melander 2020-08-23
__author__ = 'mm'


import requests
from sseclient import SSEClient
import json
import logging
from dateutil.parser import *
import yaml
import warnings
from logging.handlers import RotatingFileHandler
import sys
import sdnotify
from logging.handlers import HTTPHandler
import os
import shutil
import signal
import time

warnings.filterwarnings("ignore", category=UserWarning)

conf = yaml.load(open('auth.yml'), Loader=yaml.FullLoader)
auth_key = conf['auth']['key']

url = "https://api.trafikinfo.trafikverket.se/v2/data.json"

if len(sys.argv) == 1:
    stn_name = "Lund N" # "Gårdstånga" # "Malmö Ö" # "Lund N"
else:
    stn_name = sys.argv[1]

query = """
<REQUEST>
  <LOGIN authenticationkey='""" + auth_key + """' />
  <QUERY sseurl="true" objecttype='WeatherMeasurepoint' schemaversion='1'>
    <INCLUDE>Observation.Sample</INCLUDE>  
    <INCLUDE>Observation.Air.RelativeHumidity.Value</INCLUDE>
    <INCLUDE>Observation.Air.Temperature.Value</INCLUDE>
    <INCLUDE>Observation.Wind.Direction.Value</INCLUDE>
    <INCLUDE>Observation.Wind.Speed.Value</INCLUDE>
    <INCLUDE>Observation.Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value</INCLUDE>
    <INCLUDE>Observation.Aggregated30minutes.Wind.SpeedMax.Value</INCLUDE>
    <INCLUDE>Name</INCLUDE>
    <INCLUDE>Geometry.WGS84</INCLUDE>
    <FILTER>
        <EQ name="Name" value='""" + stn_name + """' />
    </FILTER>
  </QUERY>
</REQUEST>
"""


class Measurements:
    def __init__(self):
        self.data = []
        self.data7days = []

        signal.signal(signal.SIGHUP, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

        try:
            with open('ws.json', 'r', encoding='utf-8') as f:
                try:
                    self.data = json.load(f)
                    for d in self.data:
                        self._check(d)  # Just in case there are missing fields in the file data, should not happen
                except json.decoder.JSONDecodeError:
                    pass
        except FileNotFoundError:
            pass

        try:
            with open('ws_7d.json', 'r', encoding='utf-8') as f:
                try:
                    self.data7days = json.load(f)
                except json.decoder.JSONDecodeError:
                    pass
        except FileNotFoundError:
            pass

    def _rain(self, msr):
        if self.data:
            dt = parse(msr['Sample'])
            prev_dt = parse(self.data[-1]['Sample'])
            delta = (dt - prev_dt).total_seconds()
            if delta < 0:
                # Note, if delta < 0, we are traversing a list of data without 'Hourly'-field
                # in Precipitation (called from __init__) -> return 0
                logger.warning("Rain - delta less than zero: {}".format(delta))
                return 0
            elif delta == 0:
                # Current and previous timestamps are equal
                logger.warning("Rain - delta is zero")
                return 0
            else:
                # Calculate rain amount per hour, sum av the last 12 5-minutes periods, assuming we get a new
                # reading every 5 minute
                sum = 0
                for elem in self.data[-12:]:
                    sum += elem['Aggregated5minutes']['Precipitation']['TotalWaterEquivalent']['Value']
                return sum

        else:
            return 0

    def _check(self, msr):
        # Fields might be missing, set to default values
        if 'Aggregated5minutes' not in msr:
            msr['Aggregated5minutes'] = {}
        if 'Precipitation' not in msr['Aggregated5minutes']:
            msr['Aggregated5minutes']['Precipitation'] = {'TotalWaterEquivalent': {'Value': 0}}
        if 'TotalWaterEquivalent' not in msr['Aggregated5minutes']['Precipitation']:
            msr['Aggregated5minutes']['Precipitation']['TotalWaterEquivalent'] = {'Value': 0}

        if 'Aggregated30minutes' not in msr:
            msr['Aggregated30minutes'] = {}
        if 'Wind' not in msr['Aggregated30minutes']:
            msr['Aggregated30minutes']['Wind'] = {'SpeedMax': {'Value': None}}
        if 'SpeedMax' not in msr['Aggregated30minutes']['Wind']:
            msr['Aggregated30minutes']['Wind']['SpeedMax'] = {'Value': None}

        if 'Precipitation' not in msr:
            msr['Precipitation'] = {}
        if 'Hourly' not in msr['Precipitation']:
            msr['Precipitation']['Hourly'] = self._rain(msr)

        if 'Air' not in msr:
            msr['Air'] = {}
        if 'Temperature' not in msr['Air']:
            msr['Air']['Temperature'] = {'Value': None}
        if 'RelativeHumidity' not in msr['Air']:
            msr['Air']['RelativeHumidity'] = {'Value': None}

        if 'Wind' not in msr:
            msr['Wind'] = [{}]
        if not msr['Wind']:
            msr['Wind'].append({'Direction': {'Value': None}})
        if 'Direction' not in msr['Wind'][0]:
            msr['Wind'][0]['Direction'] = {'Value': None}
        if 'Speed' not in msr['Wind'][0]:
            msr['Wind'][0]['Speed'] = {'Value': None}

    def add(self, d):
        if 'Observation' not in d['RESPONSE']['RESULT'][0]['WeatherMeasurepoint'][0]:
            logger.warning("Corrupt measurement data - no Measurement")
            return  # Unlikely, but got a corrupt data element, do nothing

        head = d['RESPONSE']['RESULT'][0]['WeatherMeasurepoint'][0]['Observation']
        ts = head['Sample']
        dt = parse(ts)
        if self.data:
            # List will only include items the last 24 hours
            self.data = [m for m in self.data if (dt - parse(m['Sample'])).total_seconds() / 3600 <= 24.0]

        # Check head for missing fields, not all fields are included in TV responses :-(
        self._check(head)

        self.data.append(head)

        # Ugly, got to be a better way...
        # WGS84 comes as a string: "POINT(17.75481 59.81604)", first value longitude, second latitude
        # Convert into float values by first splitting string on ' ' --> ['POINT', '(17.75481', '59.81604)']
        # Then split second elem on '(' --> ['', '17.75481'], then take float of second element --> longitude
        # Same thing for latitude below
        point = d['RESPONSE']['RESULT'][0]['WeatherMeasurepoint'][0]['Geometry']['WGS84']
        point_lon = float(point.split(' ')[1].split('(')[1])
        point_lat = float(point.split(' ')[2].split(')')[0])

        self.data[-1]['geometry'] = {'lon': point_lon, 'lat': point_lat}

        if self.data7days:
            if ((dt - parse(self.data7days[0]['ts'])).total_seconds() / 3600 ) > (7 * 24.0):
                self.data7days = self.data7days[1:]  # Keep record for 7 days only

        self.data7days.append({'ts': head['Sample'],
                               'rain': head['Aggregated5minutes']['Precipitation']['TotalWaterEquivalent']['Value']})

        self._save()

    def _save(self):
        # First save to a temporary file, then save a backup of original file, then move the tmp-file to target
        fn = 'ws.json'
        with open(fn + '_tmp', 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
            f.flush()

        if os.path.exists(fn):
            shutil.move(fn, fn + '_bck')

        if os.path.exists(fn + '_tmp'):
            shutil.move(fn + '_tmp', fn)

        fn = 'ws_7days.json'
        with open(fn + '_tmp', 'w', encoding='utf-8') as f:
            json.dump(self.data7days, f, ensure_ascii=False, indent=4)
            f.flush()

        if os.path.exists(fn):
            shutil.move(fn, fn + '_bck')

        if os.path.exists(fn + '_tmp'):
            shutil.move(fn + '_tmp', fn)

    def terminate(self):
        self._save()
        sys.exit(0)


if __name__ == "__main__":
    logger = logging.getLogger("tv_ws log")
    logger.setLevel(logging.INFO)

    # add a rotating handler, max 10MB
    handler = RotatingFileHandler('ws.log', maxBytes=1048576, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    http_handler = HTTPHandler('www.viltstigen.se', '/logger/log', method='POST', secure=True)
    logger.addHandler(http_handler)

    logger.info("Start v2.1 - {}".format(stn_name))

    try:
        r = requests.post(url, data=query.encode('utf-8'), headers={'Content-Type': 'text/xml'}).json()
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError) as err:
        logger.error("Error connecting to {}".format(url))
        time.sleep(300)  # sleep for 5 min, 300 sec, before trying to reconnect
        sys.exit(1)  # General error, will make systemd to restart the service

    sse_url = r['RESPONSE']['RESULT'][0]['INFO']['SSEURL']
    # logger.info("Streaming URL: {}".format(sse_url))

    msr = Measurements()

    messages = None
    event_id = None
    url = sse_url
    msg_cnt = 0

    dog = sdnotify.SystemdNotifier()

    while True:
        try:
            if messages is None:
                messages = SSEClient(url)

            for msg in messages:
                dog.notify("WATCHDOG=1")
                if msg.data:
                    data = json.loads(msg.data)
                    msr.add(data)
                    event_id = msg.id if msg.id else event_id
                    msg_cnt = 0
                else:
                    msg_cnt += 1
                    if msg_cnt == 200:
                        logger.warning(f"TV: {stn_name}, empty msg: {msg_cnt}")
                        msg_cnt = 0

        except (ConnectionResetError, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as err:
            if event_id:
                url = sse_url + "&lasteventid=" + event_id
            else:
                url = sse_url
            logger.debug("Connection reset ({}), re-establish: {}".format(err, url))
            messages = None
            time.sleep(300) # sleep for 5 min, 300 sec, before trying to reconnect
            continue
