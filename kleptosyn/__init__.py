#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Package definitions for the `KleptoSyn` library.

see copyright/license <https://github.com/DerwenAI/kleptosyn/blob/main/LICENSE>
"""

from .sim import Simulation

from .net import Network

from .syn import SynData

from .version import get_repo_version, \
    __version__, __version_major__, __version_minor__, __version_patch__

__release__ = __version__

__title__ = "KleptoSyn: synthetic data"

__description__ = "Synthetic data generation for investigative graphs based on patterns of bad-actor tradecraft."

__copyright__ = "2025, Senzing, Inc."

__author__ = """\n""".join([
    "Paco Nathan <paco@senzing.com>"
])
