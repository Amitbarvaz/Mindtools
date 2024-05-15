'''Test settings and globals which allow us to run our test suite locally.'''
from serafin.settings import *

# Test settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_DISCOVER_TOP_LEVEL = BASE_DIR
TEST_DISCOVER_ROOT = BASE_DIR
TEST_DISCOVER_PATTERN = 'test_*'

HUEY.update({'always_eager': True})
