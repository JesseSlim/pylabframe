from . import general
from . import config

# note that this sets up a post config hook, so importing it here makes that robust
from . import data
from .data import path
