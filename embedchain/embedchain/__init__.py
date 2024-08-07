import importlib.metadata

__version__ = importlib.metadata.version("embedchain-101deploy")

from embedchain.embedchain.app import App  # noqa: F401
from embedchain.embedchain.client import Client  # noqa: F401
from embedchain.embedchain.pipeline import Pipeline  # noqa: F401
from embedchain.embedchain import *
# Setup the user directory if doesn't exist already
Client.setup()
