#!/usr/bin/python
# -*- coding: utf-8 -*-

# Mats Melander 2020-08-23
__author__ = 'mm'


import requests
from sseclient import SSEClient
import json
import logging
import dateutil
from dateutil.parser import parse
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
  <QUERY sseurl="true" objecttype='WeatherStation' schemaversion='1'>
    <INCLUDE>Measurement.Air.RelativeHumidity</INCLUDE>
    <INCLUDE>Measurement.Air.Temp</INCLUDE>  
    <INCLUDE>Measurement.MeasureTime</INCLUDE>    
    <INCLUDE>Measurement.Precipitation.Amount</INCLUDE>
    <INCLUDE>Measurement.Precipitation.AmountName</INCLUDE>
    <INCLUDE>Measurement.Precipitation.Type</INCLUDE>
    <INCLUDE>Measurement.Wind.Direction</INCLUDE>
    <INCLUDE>Measurement.Wind.Force</INCLUDE>
    <INCLUDE>Measurement.Wind.ForceMax</INCLUDE>
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
        self.ax5.set_ylabel("Wind force")
        self.ax5.grid(axis='y')

        self.windrose_fig = plt.figure(figsize=(5, 5))
        self.wr_ax = WindroseAxes.from_ax(fig=self.windrose_fig,
                                          theta_labels=THETA_LABELS)
        self.windrose_fig.add_axes(self.wr_ax)
        self.wr_ax.set_title("Wind force and directions")

    def plot(self, data):
        time = [dateutil.parser.parse(msr["MeasureTime"]) for msr in data]
        temp = [msr["Air"]["Temp"] for msr in data]
        hum = [msr["Air"]["RelativeHumidity"] for msr in data]
        rain = [msr["Precipitation"]["Amount"] for msr in data]
        rain_hourly = [msr["Precipitation"]["Hourly"] for msr in data]
        # acc_rain = [round(sum(rain[:i]), 1) for i in range(1, len(rain) + 1)]
        acc_rain_hourly = [round(sum(rain_hourly[:i]), 1) for i in range(1, len(rain) + 1)]
        wind_dir = [msr["Wind"]["Direction"] if not math.isnan(msr["Wind"]["Direction"]) else 0 for msr in data]
        wind_force = [msr["Wind"]["Force"] if not math.isnan(msr["Wind"]["Force"]) else 0 for msr in data]
        wind_force_max = [msr["Wind"]["ForceMax"] for msr in data]

        ts1 = dateutil.parser.parse(data[0]["MeasureTime"])
        wind_dir_hour = [data[0]["Wind"]["Direction"]]
        wind_time_hour = [ts1]
        wind_val_hour = [data[0]["Wind"]["Force"]]
        for msr in data:
            ts2 = dateutil.parser.parse(msr["MeasureTime"])
            if (ts2 - ts1).total_seconds() / 3600.0 > 1.0:
                wind_dir_hour.append(msr["Wind"]["Direction"])
                wind_time_hour.append(ts2)
                wind_val_hour.append(msr["Wind"]["Force"])
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

        # self.ax4.plot(time, acc_rain, color='tab:red')
        # self.ax4.annotate(str(acc_rain[0]), xy=(time[0], acc_rain[0]), color='tab:red')
        # self.ax4.annotate(str(acc_rain[-1]), xy=(time[-1], acc_rain[-1]), color='tab:red')

        self.ax4.plot(time, acc_rain_hourly, color='tab:red')
        self.ax4.annotate(str(acc_rain_hourly[-1]), xy=(time[-1], acc_rain_hourly[-1]), color='tab:red')

        self.ax5.plot(time, wind_force)
        self.ax5.plot(time, wind_force_max)

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
                                  xytext=(0, -20), textcoords='offset points')

        self.ax5.xaxis.set_major_locator(self.hours)
        self.ax5.xaxis.set_major_formatter(self.h_fmt)

        self.wr_ax.bar(wind_dir, wind_force, normed=True, opening=0.8, edgecolor='white')
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
                self.data = json.load(f)
                for d in self.data:
                    self._check(d)  # Just in case there are missing fields in the file data, should not happen
        except FileNotFoundError:
            pass

    def _rain(self, msr):
        if self.data:
            dt = dateutil.parser.parse(msr['MeasureTime'])
            prev_dt = dateutil.parser.parse(self.data[-1]['MeasureTime'])
            delta = (dt - prev_dt).total_seconds()
            if delta < 0:
                # Note, if delta < 0, we are traversing a list of data without 'Hourly'-field
                # in Precipitation (called from __init__) -> return 0
                logger.warning("Rain - delta less than zero: {}".format(delta))
                return float("Nan")
            elif delta == 0:
                # Current and previous timestamps are equal
                logger.warning("Rain - delta is zero")
                return 0
            else:
                # Calculate rain amount per hour, assuming 'Amount' is _intensity_ of rain
                # Eg if Amount == 1.0 and previous reading were 10 minutes ago, it has rained 1 / 10min this period
                return msr['Precipitation']['Amount'] *  (delta / 3600.0)
        else:
            return float("Nan")

    def _check(self, msr):
        # Fields might be missing, set to default values
        if 'Precipitation' not in msr:
            msr['Precipitation'] = {}
        if 'Amount' not in msr['Precipitation']:
            msr['Precipitation']['Amount'] = 0  # TV doesn't include Amount value if it is not raining :-(
        if 'AmountName' not in msr['Precipitation']:
            msr['Precipitation']['AmountName'] = ""
        if 'Type' not in msr['Precipitation']:
            msr['Precipitation']['Type'] = ""
        if 'Hourly' not in msr['Precipitation']:
            msr['Precipitation']['Hourly'] = self._rain(msr)

        if 'Air' not in msr:
            msr['Air'] = {}
        if 'Temp' not in msr['Air']:
            msr['Air']['Temp'] = float("NaN")
        if 'RelativeHumidity' not in msr['Air']:
            msr['Air']['RelativeHumidity'] = float("NaN")

        if 'Wind' not in msr:
            msr['Wind'] = {}
        if 'Direction' not in msr['Wind']:
            msr['Wind']['Direction'] = float("NaN")
        if 'Force' not in msr['Wind']:
            msr['Wind']['Force'] = float("NaN")
        if 'ForceMax' not in msr['Wind']:
            msr['Wind']['ForceMax'] = float("Nan")

    def add(self, d):
        if 'Measurement' not in d['RESPONSE']['RESULT'][0]['WeatherStation'][0]:
            logger.warning("Corrupt measurement data - no Measurement")
            return  # Unlikely, but got a corrupt data element, do nothing

        head = d['RESPONSE']['RESULT'][0]['WeatherStation'][0]['Measurement']
        ts = head['MeasureTime']
        dt = dateutil.parser.parse(ts)
        if self.data:
            # List will only include items the last 24 hours
            self.data = [m for m in self.data
                         if (dt - dateutil.parser.parse(m['MeasureTime'])).total_seconds() / 3600 <= 24.0]

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

    logger.info("Start v0.9")
    logger.info("Station: {}".format(stn_name))

    r = requests.post(url, data=query.encode('utf-8'), headers={'Content-Type': 'text/xml'}).json()
    sse_url = r['RESPONSE']['RESULT'][0]['INFO']['SSEURL']
    logger.info("Streaming URL: {}".format(sse_url))

    msr = Measurements()

    messages = SSEClient(sse_url)
    event_id = None

    bins = numpy.linspace(0, 360, len(WIND_LABELS))

    while True:
        try:
            for msg in messages:
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
                        first_time = dateutil.parser.parse(msr.data[0]["MeasureTime"])
                        last_time = dateutil.parser.parse(msr.data[-1]["MeasureTime"])

                        # Boring string management for presentation..., the ones with suffix '_str' is visualized
                        h2_str = first_time.strftime("%Y-%m-%d %H:%M:%S") + " - " + \
                                 last_time.strftime("%Y-%m-%d %H:%M:%S")

                        air_temp_str = str(msr.data[-1]["Air"]["Temp"]) + "°C" \
                            if not math.isnan(msr.data[-1]["Air"]["Temp"]) else ""
                        air_relhum_str = str(msr.data[-1]["Air"]["RelativeHumidity"]) + "%" \
                            if not math.isnan(msr.data[-1]["Air"]["RelativeHumidity"]) else ""

                        rain_amount = str(msr.data[-1]["Precipitation"]["Amount"]) + "mm" \
                            if not math.isnan(msr.data[-1]["Precipitation"]["Amount"]) else ""
                        if rain_amount != "":
                            rain_type = msr.data[-1]["Precipitation"]["Type"]
                            rain_name = msr.data[-1]["Precipitation"]["AmountName"]
                            rain_descr = rain_type + " - " + rain_name if rain_type != rain_name else rain_type
                            rain_str = rain_amount + " (" + rain_descr + ")"
                        else:
                            rain_str = ""

                        bin = numpy.digitize(msr.data[-1]["Wind"]["Direction"], bins)
                        # bin can be out of index if "Direction" == "NaN"
                        wd_label = WIND_LABELS[bin] if bin < len(WIND_LABELS) else ""

                        wd_dir = str(msr.data[-1]["Wind"]["Direction"]) + "°" \
                            if not math.isnan(msr.data[-1]["Wind"]["Direction"]) else ""
                        wd_label_dir_str = wd_label if wd_dir == "" else wd_label + " (" + wd_dir + ")"
                        wd_force_str = str(msr.data[-1]["Wind"]["Force"]) + "m/s" \
                            if not math.isnan(msr.data[-1]["Wind"]["Force"]) else ""
                        wd_force_max_str = str(msr.data[-1]["Wind"]["ForceMax"]) + "m/s" \
                            if not math.isnan(msr.data[-1]["Wind"]["ForceMax"]) else ""

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
                                                          wd_force_str,
                                                          wd_force_max_str
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
