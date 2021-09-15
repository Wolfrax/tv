#!/usr/bin/python
# -*- coding: utf-8 -*-

# Mats Melander 2020-08-23, 2021-09-15
__author__ = 'mm'

import json
import logging
import os
from flask import Flask, render_template, request, abort


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


@app.route('/')
def index():
    stn = request.args.get('stn', '')

    if stn == '':
        abort(404, description="Resource not found")
    elif stn == 'Lund':
        return render_template('ws.html', stn=stn, title='Weather Lund N')
    elif stn == 'Ralla':
        return render_template('ws.html', stn=stn, title='Weather Öland Rälla')
    elif stn == 'Uppsala':
        return render_template('ws.html', stn=stn, title='Weather Uppsala Sävjaån')
    else:
        abort(404, description="Resource not found")

