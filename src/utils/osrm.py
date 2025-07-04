#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests

DEFAULT_IP = "0.0.0.0"
DEFAULT_PORT = "5000"


def format_request(service, locs, ip=DEFAULT_IP, port=DEFAULT_PORT, profile="car"):
    port_string = ":" + port if port else ""
    req = "http://" + ip + port_string + "/"
    req += service + "/v1/" + profile + "/"
    for loc in locs:
        req += str(loc[0]) + "," + str(loc[1]) + ";"

    return req[:-1]


def route(locs, extra_args="", ip=DEFAULT_IP, port=DEFAULT_PORT):
    # Building request.
    req = format_request("route", locs, ip, port)

    req += "?alternatives=false&steps=false&overview=full&continue_straight=false"
    req += extra_args

    res = requests.get(req)
    res.raise_for_status()

    return res.json()


def table(locs, ip=DEFAULT_IP, port=DEFAULT_PORT, profile="car"):
    req = format_request("table", locs, ip, port, profile)

    req += "?annotations=duration,distance"

    res = requests.get(req)
    res.raise_for_status()

    return res.json()
