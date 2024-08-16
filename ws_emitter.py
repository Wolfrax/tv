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

    return {'data': obs} if ind == '' else {'data': obs[int(ind):]}


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
        return render_template('ws.html', stn=stn, title='Weather Lund (Malmö Ö)')
    elif stn == 'Karlshamn':
        return render_template('ws.html', stn=stn, title='Weather Karlshamn')
    elif stn == 'Ralla':
        return render_template('ws.html', stn=stn, title='Weather Öland Rälla')
    elif stn == 'Uppsala':
        return render_template('ws.html', stn=stn, title='Weather Uppsala Sävjaån')
    else:
        abort(404, description="Resource not found")

