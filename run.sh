#!/bin/sh
# -*- coding: utf-8 -*-

if [[ -a bin/activate ]]; then
	source bin/activate
	bin/python ./start_micropsi_server.py
else
	bin/python ./start_micropsi_server.py
fi
