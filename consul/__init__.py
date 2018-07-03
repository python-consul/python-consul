__version__ = '1.1.0-dev'

from consul.std import Consul

from consul.base import Check

from consul.base import ConsulException
from consul.base import ACLPermissionDenied
from consul.base import ACLDisabled
from consul.base import NotFound
from consul.base import Timeout
