# Copyright 2013 University of California at Berkeley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Geocoding service."""

import json
import urllib
from google.appengine.api import urlfetch
from geomancer.model import Cache

class Geocode(Cache):
    """Cache model for geocode results."""
    pass

def get_url(feature):
    params = [('address', feature.encode('utf-8')), ('sensor', 'false')]
    encoded_params = urllib.urlencode(params)
    url = 'http://maps.googleapis.com/maps/api/geocode/json?%s' % encoded_params

def lookup(features):
    """Return geocode results for supplied feature name."""    
    geocode = Geocode.get_or_insert(feature)
    if geocode.results:
        return geocode.results
    params = urllib.urlencode([('address', feature.encode('utf-8')), ('sensor', 'false')])
    url = 'http://maps.googleapis.com/maps/api/geocode/json?%s' % params
    geocode.results = json.loads(urlfetch.fetch(url).content)
    geocode.put()
    return geocode.results