#!/usr/bin/python
# -*- coding: utf-8 -*-

# Mats Melander 2020-08-23
__author__ = 'mm'


import requests
from sseclient import SSEClient
import json
import logging
import dateutil
import matplotlib.pyplot as plt
import matplotlib
from windrose import WindroseAxes
import matplotlib.dates as mdates
import yaml
from flask import Flask, render_template
import numpy
from matplotlib.markers import MarkerStyle
from multiprocessing import Process
import warnings
import resource
from logging.handlers import RotatingFileHandler
import sys
import math
import sdnotify


# For checking system usage, like memory: print(usage("Plot")
def using(point=""):
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return '''%s: usertime=%s systime=%s mem=%s mb''' % (point, usage[0], usage[1], usage[2]/1024.0 )


warnings.filterwarnings("ignore", category=UserWarning)

app = Flask(__name__)

conf = yaml.load(open('auth.yml'), Loader=yaml.FullLoader)
auth_key = conf['auth']['key']

url = "https://api.trafikinfo.trafikverket.se/v2/data.json"

if len(sys.argv) == 1:
    stn_name = "Lund N"
else:
    stn_name = sys.argv[1]

print("Station: {}".format(stn_name))

query = """
<REQUEST>
  <LOGIN authenticationkey='""" + auth_key + """' />
  <QUERY sseurl="true" objecttype='WeatherMeasurepoint' schemaversion='1'>
    <INCLUDE>Observation.Sample</INCLUDE>  
    <INCLUDE>Observation.Air.RelativeHumidity.Value</INCLUDE>
    <INCLUDE>Observation.Air.Temperature.Value</INCLUDE>
    <INCLUDE>Observation.Wind.Direction.Value</INCLUDE>
    <INCLUDE>Observation.Wind.Speed.Value</INCLUDE>
    <INCLUDE>Observation.Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value</INCLUDE>
    <INCLUDE>Observation.Aggregated30minutes.Wind.SpeedMax.Value</INCLUDE>
    <INCLUDE>Name</INCLUDE>
    <FILTER>
        <EQ name="Name" value='""" + stn_name + """' />
    </FILTER>
  </QUERY>
</REQUEST>
"""

THETA_LABELS = ["E", "N-E", "N", "N-W", "W", "S-W", "S", "S-E"]
WIND_DEGREES = [90, 45, 0, 315, 270, 225, 180, 135]
WIND_LABELS = ["N", "N-E", "E", "S-E", "S", "S-W" , "W", "N-W"]


class Graph:
    def __init__(self):
        # Instantiate 2 figures
        # Figure 1: 2 subplots (Temp/Humidity and Rain) with 4 axis (ax1 - ax4)
        # Figure 2: 1 subplot (Windrose) with 1 axis (ax5)

        matplotlib.rcParams['timezone'] = '+2:00'

        self.hours = mdates.HourLocator(interval=1)
        self.h_fmt = mdates.DateFormatter('%H:%M')

        self.temp_rain_fig = plt.figure(figsize=(10, 15))

        self.ax1 = plt.subplot(3, 1, 1)
        self.temp_rain_fig.add_axes(self.ax1)

        self.ax1.tick_params(axis='x', labelrotation=45)
        self.ax1.set_title("Temperature and Humidity")
        self.ax1.set_ylabel('Temp')
        self.ax1.grid(axis='y')

        self.ax2 = self.ax1.twinx()
        self.temp_rain_fig.add_axes(self.ax2)

        self.ax2.set_ylabel('Humidity', color='tab:red')
        # self.ax2.grid(axis='y')

        self.ax3 = plt.subplot(3, 1, 2, sharex=self.ax1)
        self.temp_rain_fig.add_axes(self.ax3)

        self.ax3.tick_params(axis='x', labelrotation=45)
        self.ax3.set_title("Rain")
        self.ax3.set_ylabel("Rain")
        self.ax3.grid(axis='y')

        self.ax4 = self.ax3.twinx()
        self.temp_rain_fig.add_axes(self.ax4)
        self.ax4.set_ylabel('Accumulated rain', color='tab:red')
        self.ax4.tick_params(axis='y', labelcolor='tab:red')

        self.ax5 = plt.subplot(3, 1, 3, sharex=self.ax1)
        self.temp_rain_fig.add_axes(self.ax5)

        self.ax5.tick_params(axis='x', labelrotation=45)
        self.ax5.set_title("Wind")
        self.ax5.set_ylabel("Wind speed")
        self.ax5.grid(axis='y')

        self.windrose_fig = plt.figure(figsize=(5, 5))
        self.wr_ax = WindroseAxes.from_ax(fig=self.windrose_fig,
                                          theta_labels=THETA_LABELS)
        self.windrose_fig.add_axes(self.wr_ax)
        self.wr_ax.set_title("Wind speed and directions")

    def plot(self, data):
        time = [dateutil.parser.parse(msr["Sample"]) for msr in data]
        temp = [msr["Air"]["Temperature"]["Value"] for msr in data]
        hum = [msr["Air"]["RelativeHumidity"]["Value"] for msr in data]

        rain = [msr['Aggregated10minutes']['Precipitation']['TotalWaterEquivalent']['Value'] for msr in data]
        acc_rain = numpy.round(numpy.cumsum(rain), decimals=1)

        wind_dir = [msr["Wind"][0]["Direction"]["Value"]
                    if not math.isnan(msr["Wind"][0]["Direction"]["Value"]) else 0 for msr in data]
        wind_speed = [msr["Wind"][0]["Speed"]["Value"]
                      if not math.isnan(msr["Wind"][0]["Speed"]["Value"]) else 0 for msr in data]
        wind_speed_max = [msr["Aggregated30minutes"]["Wind"]["SpeedMax"]["Value"] for msr in data]

        ts1 = dateutil.parser.parse(data[0]["Sample"])
        wind_dir_hour = [data[0]["Wind"][0]["Direction"]["Value"]]
        wind_time_hour = [ts1]
        wind_val_hour = [data[0]["Wind"][0]["Speed"]["Value"]]
        for msr in data:
            ts2 = dateutil.parser.parse(msr["Sample"])
            if (ts2 - ts1).total_seconds() / 3600.0 > 1.0:
                wind_dir_hour.append(msr["Wind"][0]["Direction"]["Value"])
                wind_time_hour.append(ts2)
                wind_val_hour.append(msr["Wind"][0]["Speed"]["Value"])
                ts1 = ts2

        self.ax1.plot(time, temp)
        self.ax1.annotate(str(temp[0]), xy=(time[0], temp[0]))
        self.ax1.annotate(str(temp[-1]), xy=(time[-1], temp[-1]))

        max_idx = temp.index(max(temp))
        min_idx = temp.index(min(temp))
        self.ax1.annotate(str(temp[max_idx]), xy=(time[max_idx], temp[max_idx]))
        self.ax1.annotate(str(temp[min_idx]), xy=(time[min_idx], temp[min_idx]))

        self.ax2.plot(time, hum, color='tab:red')
        self.ax2.annotate(str(hum[0]), xy=(time[0], hum[0]), color='tab:red')
        self.ax2.annotate(str(hum[-1]), xy=(time[-1], hum[-1]), color='tab:red')
        max_idx = hum.index(max(hum))
        min_idx = hum.index(min(hum))
        self.ax2.annotate(str(hum[max_idx]), xy=(time[max_idx], hum[max_idx]), color='tab:red')
        self.ax2.annotate(str(hum[min_idx]), xy=(time[min_idx], hum[min_idx]), color='tab:red')

        self.ax3.plot(time, rain)
        max_idx = rain.index(max(rain))
        self.ax3.annotate(str(rain[max_idx]), xy=(time[max_idx], rain[max_idx]))

        self.ax4.plot(time, acc_rain, color='tab:red')
        self.ax4.annotate(str(acc_rain[-1]), xy=(time[-1], acc_rain[-1]), color='tab:red')

        self.ax5.plot(time, wind_speed)
        self.ax5.plot(time, wind_speed_max)

        bins = numpy.linspace(0, 360, len(WIND_LABELS))
        for i, v in enumerate(wind_dir_hour):
            bin = numpy.digitize(wind_dir_hour[i], bins)
            # bin can be out of index if "Direction" == "NaN"
            if bin < len(WIND_DEGREES):
                m = MarkerStyle(r'$\leftarrow$')
                m._transform.rotate_deg(WIND_DEGREES[bin])
                self.ax5.plot(wind_time_hour[i], wind_val_hour[i],
                              marker=m,
                              markersize=20,
                              linestyle='None', color='crimson')

        for i, dir in enumerate(wind_dir_hour):
            bin = numpy.digitize(wind_dir_hour[i], bins)
            if bin < len(WIND_LABELS):
                self.ax5.annotate(WIND_LABELS[bin], (wind_time_hour[i], wind_val_hour[i]),
                                  xytext=(0, 15), textcoords='offset points')

        self.ax5.xaxis.set_major_locator(self.hours)
        self.ax5.xaxis.set_major_formatter(self.h_fmt)

        self.wr_ax.bar(wind_dir, wind_speed, normed=True, opening=0.8, edgecolor='white')
        self.wr_ax.set_legend()

    def save(self):
        self.temp_rain_fig.savefig('ws.png')
        self.windrose_fig.savefig('ws_windrose.png')

    def show(self):
        plt.subplots_adjust(hspace=0.5) #top=0.85)
        plt.show()

    def close(self):
        plt.close('all')


class Measurements:
    def __init__(self):
        self.data = []

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

    def _rain(self, msr):
        if self.data:
            dt = dateutil.parser.parse(msr['Sample'])
            prev_dt = dateutil.parser.parse(self.data[-1]['Sample'])
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
                # Calculate rain amount per hour, sum av the last 6 10 minutes periods, assuming we get a new
                # reading every 10 minute
                sum = 0
                for elem in self.data[-6:]:
                    sum += elem['Aggregated10minutes']['Precipitation']['TotalWaterEquivalent']['Value']
                return sum

        else:
            return 0

    def _check(self, msr):
        # Fields might be missing, set to default values
        if 'Aggregated10minutes' not in msr:
            msr['Aggregated10minutes'] = {}
        if 'Precipitation' not in msr['Aggregated10minutes']:
            msr['Aggregated10minutes']['Precipitation'] =  {'TotalWaterEquivalent': {'Value': 0}}
        if 'TotalWaterEquivalent' not in msr['Aggregated10minutes']['Precipitation']:
            msr['Aggregated10minutes']['Precipitation']['TotalWaterEquivalent'] = {'Value': 0}

        if 'Aggregated30minutes' not in msr:
            msr['Aggregated30minutes'] = {}
        if 'Wind' not in msr['Aggregated30minutes']:
            msr['Aggregated30minutes']['Wind'] = {'SpeedMax': {'Value': 0}}
        if 'SpeedMax' not in msr['Aggregated30minutes']['Wind']:
            msr['Aggregated30minutes']['Wind']['SpeedMax'] = {'Value': 0}

        if 'Precipitation' not in msr:
            msr['Precipitation'] = {}
        if 'Hourly' not in msr['Precipitation']:
            msr['Precipitation']['Hourly'] = self._rain(msr)

        if 'Air' not in msr:
            msr['Air'] = {}
        if 'Temperature' not in msr['Air']:
            msr['Air']['Temperature'] = {'Value': float("NaN")}
        if 'RelativeHumidity' not in msr['Air']:
            msr['Air']['RelativeHumidity'] = {'Value': float("NaN")}

        if 'Wind' not in msr:
            msr['Wind'] = [{}]
        if not msr['Wind']:
            msr['Wind'].append({'Direction': {'Value': float("NaN")}})
        if 'Direction' not in msr['Wind'][0]:
            msr['Wind'][0]['Direction'] = {'Value': float("NaN")}
        if 'Speed' not in msr['Wind'][0]:
            msr['Wind'][0]['Speed'] = {'Value': float("NaN")}

    def add(self, d):
        if 'Observation' not in d['RESPONSE']['RESULT'][0]['WeatherMeasurepoint'][0]:
            logger.warning("Corrupt measurement data - no Measurement")
            return  # Unlikely, but got a corrupt data element, do nothing

        head = d['RESPONSE']['RESULT'][0]['WeatherMeasurepoint'][0]['Observation']
        ts = head['Sample']
        dt = dateutil.parser.parse(ts)
        if self.data:
            # List will only include items the last 24 hours
            self.data = [m for m in self.data
                         if (dt - dateutil.parser.parse(m['Sample'])).total_seconds() / 3600 <= 24.0]

        # Check head for missing fields, not all fields are included in TV responses :-(
        self._check(head)

        self.data.append(head)

        with open('ws.json', 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
            f.flush()


def do_graph(m):
    gr = Graph()
    gr.plot(m.data)
    gr.save()
    gr.close()


if __name__ == "__main__":
    logger = logging.getLogger("tv_ws log")
    logger.setLevel(logging.DEBUG)

    # add a rotating handler, max 10MB
    handler = RotatingFileHandler('ws.log', maxBytes=1048576, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # In case of loggin to /var/log/syslog
    # handler = logging.handlers.SysLogHandler(address='/dev/log')
    # handler.setFormatter(formatter)
    # handler.setLevel(logging.DEBUG)
    # logger.addHandler(handler)

    logger.info("Start v1.0")
    logger.info("Station: {}".format(stn_name))

    r = requests.post(url, data=query.encode('utf-8'), headers={'Content-Type': 'text/xml'}).json()
    sse_url = r['RESPONSE']['RESULT'][0]['INFO']['SSEURL']
    logger.info("Streaming URL: {}".format(sse_url))

    msr = Measurements()

    messages = SSEClient(sse_url)
    event_id = None

    bins = numpy.linspace(0, 360, len(WIND_LABELS))

    dog = sdnotify.SystemdNotifier()

    while True:
        try:
            for msg in messages:
                dog.notify("WATCHDOG=1")
                if msg.data:
                    data = json.loads(msg.data)
                    msr.add(data)

                    # Do plotting in a separate process, this will allocate/deallocate memory used by matplotlib
                    # If we do this in the 'while True' loop, we need to explicitly release memory and do
                    # garbage collection (del obj, gc.collect())
                    p = Process(target=do_graph, args=(msr,))
                    p.start()
                    p.join(timeout=120)  # kill after 2 minutes
                    if p.exitcode is not None and p.exitcode < 0:
                        logging.warning("Graphical process - exit on timeout, is_alive is {}".format(p.is_alive()))
                        if p.is_alive(): p.kill()

                    with app.app_context():
                        first_time = dateutil.parser.parse(msr.data[0]["Sample"])
                        last_time = dateutil.parser.parse(msr.data[-1]["Sample"])

                        # Boring string management for presentation..., the ones with suffix '_str' is visualized
                        h2_str = first_time.strftime("%Y-%m-%d %H:%M:%S") + " - " + \
                                 last_time.strftime("%Y-%m-%d %H:%M:%S")

                        air_temp_str = str(msr.data[-1]["Air"]["Temperature"]["Value"]) + "°C" \
                            if not math.isnan(msr.data[-1]["Air"]["Temperature"]["Value"]) else ""
                        air_relhum_str = str(msr.data[-1]["Air"]["RelativeHumidity"]["Value"]) + "%" \
                            if not math.isnan(msr.data[-1]["Air"]["RelativeHumidity"]["Value"]) else ""

                        rain = [msr['Aggregated10minutes']['Precipitation']['TotalWaterEquivalent']['Value'] for msr in
                                msr.data]
                        acc_rain = str(numpy.round(numpy.cumsum(rain), decimals=1)[-1])
                        rain_str = str(
                            msr.data[-1]['Aggregated10minutes']['Precipitation']['TotalWaterEquivalent']['Value']) + \
                                   "mm" + " (" + acc_rain + "mm)"

                        bin = numpy.digitize(msr.data[-1]["Wind"][0]["Direction"]["Value"], bins)
                        # bin can be out of index if "Direction" == "NaN"
                        wd_label = WIND_LABELS[bin] if bin < len(WIND_LABELS) else ""

                        wd_dir = str(msr.data[-1]["Wind"][0]["Direction"]["Value"]) + "°" \
                            if not math.isnan(msr.data[-1]["Wind"][0]["Direction"]["Value"]) else ""
                        wd_label_dir_str = wd_label if wd_dir == "" else wd_label + " (" + wd_dir + ")"
                        wd_speed_str = str(msr.data[-1]["Wind"][0]["Speed"]["Value"]) + "m/s" \
                            if not math.isnan(msr.data[-1]["Wind"][0]["Speed"]["Value"]) else ""
                        wd_speed_max_str = str(msr.data[-1]["Aggregated30minutes"]["Wind"]["SpeedMax"]["Value"]) + "m/s" \
                            if not math.isnan(msr.data[-1]["Aggregated30minutes"]["Wind"]["SpeedMax"]["Value"]) else ""

                        html_file = render_template('ws_template.html',
                                                    title=stn_name,
                                                    head='Weather ' + stn_name + ' last 24 hours',
                                                    head2=h2_str,
                                                    images=['ws.png', 'ws_windrose.png'],
                                                    data=[last_time.strftime("%Y-%m-%d %H:%M:%S"),
                                                          air_temp_str,
                                                          air_relhum_str,
                                                          rain_str,
                                                          wd_label_dir_str,
                                                          wd_speed_str,
                                                          wd_speed_max_str
                                                          ])

                        with open('ws.html', encoding='utf-8', mode='w') as outfile:
                            outfile.write(html_file)

                    event_id = msg.id if msg.id else event_id

        except ConnectionResetError:
            if event_id:
                url = sse_url + "&lasteventid=" + event_id
            else:
                url = sse_url
            logger.info("Connection reset, re-establish: {}".format(url))
            messages = SSEClient(url)
