#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from api import api
from config import Config
from console import console
from webui import webui


def run():
    """Run the program."""
    cfg = Config()

    mode = cfg.mode
    if mode == 'console':
        console(cfg)
    elif mode == 'api':
        api(cfg)
    elif mode == 'webui':
        webui(cfg)
    else:
        raise ValueError('mode must be console or api')


if __name__ == '__main__':
    run()
