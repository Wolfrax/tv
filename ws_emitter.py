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


class ReverseProxied(object):
    def __init__(self, app, script_name):
        self.app = app
        self.script_name = script_name

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.script_name
        return self.app(environ, start_response)

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['APPLICATION_ROOT'] = '/tv_ws'
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)


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

def par_filter_OLD(lst, par):
    return next(item for item in lst['parameters'] if item['name'] == par)['values'][0]

@app.route('/_fc_OLD')
def fc_OLD():
    lat = request.args.get('lat', '')
    lon = request.args.get('lon', '')

    if lat == '' or lon == '':
        abort(404, description="Resource not found")

    #           https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/16/lat/58/data.json
    site_url = "https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon}/lat/{lat}/data.json"
    #site_url = "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"
    data_url = uritemplate.expand(site_url, lon=lon, lat=lat)

    from flask import current_app

    try:
        r = requests.get(data_url, timeout=10)

        # 🔍 LOG BEFORE parsing
        current_app.logger.error(f"STATUS: {r.status_code}")
        current_app.logger.error(f"CONTENT: {r.text[:500]}")

        r.raise_for_status()  # catches HTTP errors

        data = r.json()

        res = []
        for par in data['timeSeries']:
            res.append({
                'time': par['validTime'],
                'temp': par_filter_OLD(par, 't'),
                'hum': par_filter_OLD(par, 'r'),
                'rain': par_filter_OLD(par, 'pmax'),
                'wind_speed': par_filter_OLD(par, 'ws'),
                'wind_dir': par_filter_OLD(par, 'wd'),
                'wind_max': par_filter_OLD(par, 'gust')
            })

        return jsonify({'data': res})

    except Exception as e:
        current_app.logger.exception("SMHI request failed")
        return jsonify({'error': str(e)}), 500

def par_filter(lst, par):
    return next(item for item in lst['data'] if item['name'] == par)['values'][0]

@app.route('/_fc')
def fc():
    lat = request.args.get('lat', '')
    lon = request.args.get('lon', '')

    if lat == '' or lon == '':
        abort(404, description="Resource not found")
    else:
        #           https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/13.2242/lat/55.81807/data.json
        site_url = "https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon}/lat/{lat}/data.json"
        #site_url = "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"

        data_url = uritemplate.expand(site_url, lon=lon, lat=lat)
        try:
            # "https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{lon}/lat/{lat}/data.json"
            r = requests.get(
                data_url,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            from flask import current_app
            current_app.logger.error(f"URL: {data_url}")
            current_app.logger.error(f"STATUS: {r.status_code}")
            current_app.logger.error(f"CONTENT: {r.text[:500]}")

            r.raise_for_status()
            data = r.json()

            #data = requests.get(data_url).json()
            #from flask import current_app

            #current_app.logger.error(f"STATUS: {r.status_code}")
            #current_app.logger.error(f"CONTENT: {r.text[:500]}")
            
            res = []
            for par in data['timeSeries']:
                res.append({'time': par['time'],
                            'temp': par_filter(par, 'air_temperature'),
                            'hum': par_filter(par, 'relative_humidity'),
                            'rain': par_filter(par, 'precipitation_amount_max'),
                            'wind_speed': par_filter(par, 'wind_speed'),
                            'wind_dir': par_filter(par, 'wind_from_direction'),
                            'wind_max': par_filter(par, 'wind_speed_of_gust')})
            return jsonify({'data': res})
        except requests.HTTPError:
            logging.warning("HTTPError")
            abort(404, description="Resource not found")

import os

@app.route('/')
def index():
    mapbox_token = os.environ.get("MAPBOX_TOKEN")
    stn = request.args.get('stn', '')

    if stn == '':
        abort(404, description="Resource not found")
    elif stn == 'Lund':
        return render_template('ws.html', stn=stn, title='Weather Lund', mapbox_token=mapbox_token)
    elif stn == 'Karlshamn':
        return render_template('ws.html', stn=stn, title='Weather Karlshamn', mapbox_token=mapbox_token)
    elif stn == 'Ralla':
        return render_template('ws.html', stn=stn, title='Weather Öland', mapbox_token=mapbox_token)
    elif stn == 'Uppsala':
        return render_template('ws.html', stn=stn, title='Weather Uppsala', mapbox_token=mapbox_token)
    else:
        abort(404, description="Resource not found")

