import os
import sys

for name in ['oauth2', 'python-gflags-2.0', 'google-api-python-client-1.0', 
	'httplib2', 'cartodb']:
	sys.path.append(os.path.join(os.path.dirname(__file__), 'lib', name))
