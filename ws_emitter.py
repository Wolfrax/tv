#!/usr/bin/python
# -*- coding: utf-8 -*-

# Mats Melander 2020-08-23, 2021-09-15
__author__ = 'mm'

import json
import logging

from flask import Flask, request, abort, jsonify, render_template
import requests
import uritemplate
from logging.handlers import HTTPHandler
from dateutil import parser

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

http_handler = HTTPHandler('www.viltstigen.se', '/logger/log', method='POST', secure=True)
_LOGGER.addHandler(http_handler)


class ReverseProxied(object):
    def __init__(self, app, script_name):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.script_name
        return self.app(environ, start_response)


app = Flask(__name__)
app.wsgi_app = ReverseProxied(app.wsgi_app, script_name='/tv_ws')


@app.route('/_ws')
def emit():
    ind = request.args.get('ind', '')
    stn = request.args.get('stn', '')

    stn = '.' if stn == 'Lund' else './' + stn

    with open(stn + '/ws.json') as f:
        obs = json.load(f)
        if ind == '':  # Return full series
            return {'data': obs}
        elif int(ind) < 0:  # Return last ind items
            return {'data': obs[int(ind):]}
        else:  # Return last ind hours
            last_dt = parser.parse(obs[-1]['Sample'])
            i = 0
            for item in obs:
                if (last_dt - parser.parse(item['Sample'])).total_seconds() <= int(ind) * 60 * 60:
                    i-= 1
            return {'data': obs[i:]}

@app.route('/_ws7days')
def emit_7days():
    ind = request.args.get('ind', '')
    stn = request.args.get('stn', '')

    stn = '.' if stn == 'Lund' else './' + stn

    with open(stn + '/ws_7days.json') as f:
        obs = json.load(f)
        if ind == '':  # Return full series
            return {'data': obs}
        elif int(ind) < 0:  # Return last ind items
            return {'data': obs[int(ind):]}
        else:  # Return last ind days
            last_dt = parser.parse(obs[-1]['ts'])
            i = 0
            for item in obs:
                if (last_dt - parser.parse(item['ts'])).total_seconds() <= int(ind) * 24 * 60 * 60:
                    i-= 1
            return {'data': obs[i:]}

@app.route('/_ws7dayssum')
def emit_7dayssum():
    ind = request.args.get('ind', '')
    stn = request.args.get('stn', '')

    stn = '.' if stn == 'Lund' else './' + stn
    rain_sum = 0

    with open(stn + '/ws_7days.json') as f:
        obs = json.load(f)
        if ind == '':  # Return full series
            for elem in obs:
                rain_sum += float(elem['rain'])
            return {'data': rain_sum}
        elif int(ind) < 0:  # Return last ind items, not verified!
            for elem in obs[int(ind):]:
                rain_sum += int(elem['rain'])
            return {'data': rain_sum}
        else:  # Return last ind days, not verified!
            last_dt = parser.parse(obs[-1]['ts'])
            i = 0
            for item in obs:
                if (last_dt - parser.parse(item['ts'])).total_seconds() <= int(ind) * 24 * 60 * 60:
                    i-= 1
            return {'data': obs[i:]}

def par_filter(lst, par):
    return next(item for item in lst['parameters'] if item['name'] == par)['values'][0]


@app.route('/_fc')
def fc():
    lat = request.args.get('lat', '')
    lon = request.args.get('lon', '')

    if lat == '' or lon == '':
        abort(404, description="Resource not found")
    else:
        site_url = "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"

        data_url = uritemplate.expand(site_url, lon=lon, lat=lat)
        try:
            # "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"
            data = requests.get(data_url).json()
            res = []
            for par in data['timeSeries']:
                res.append({'time': par['validTime'],
                            'temp': par_filter(par, 't'),
                            'hum': par_filter(par, 'r'),
                            'rain': par_filter(par, 'pmax'),
                            'wind_speed': par_filter(par, 'ws'),
                            'wind_dir': par_filter(par, 'wd'),
                            'wind_max': par_filter(par, 'gust')})
            return jsonify({'data': res})
        except requests.HTTPError:
            logging.warning("HTTPError")
            abort(404, description="Resource not found")


@app.route('/')
def index():
    stn = request.args.get('stn', '')

    if stn == '':
        abort(404, description="Resource not found")
    elif stn == 'Lund':
        return render_template('ws.html', stn=stn, title='Weather Lund')
    elif stn == 'Karlshamn':
        return render_template('ws.html', stn=stn, title='Weather Karlshamn')
    elif stn == 'Ralla':
        return render_template('ws.html', stn=stn, title='Weather Öland')
    elif stn == 'Uppsala':
        return render_template('ws.html', stn=stn, title='Weather Uppsala')
    else:
        abort(404, description="Resource not found")

