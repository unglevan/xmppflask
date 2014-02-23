# -*- coding: utf-8 -*-

import logging
import sys

if sys.version_info >= (2, 7):
    unittest = __import__('unittest')
else:
    unittest = __import__('unittest2')

logging.disable(logging.CRITICAL)
