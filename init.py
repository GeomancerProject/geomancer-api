import os
import sys

# Add libs to path:
def setup():
	for name in ['python-gflags-2.0', 'google-api-python-client-1.0', 'httplib2']:
		sys.path.append(os.path.join(os.path.dirname(__file__), 'lib', name))

