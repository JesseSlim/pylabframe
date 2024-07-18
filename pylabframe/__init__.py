"""pyLabFrame is a Python package to help you interact with laboratory instruments and measurement data."""

from . import general
from . import config

# note that this sets up a post config hook, so importing it here makes that robust
from . import data
from .data import path
