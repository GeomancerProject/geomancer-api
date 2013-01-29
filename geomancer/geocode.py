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

"""Geocoding service using parallel async urlfetching."""

import json
import urllib
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from geomancer.model import Cache

class Geocode(Cache):
    """Cache model for geocode results."""
    pass

def get_url(feature):
    params = [('address', feature.encode('utf-8')), ('sensor', 'false')]
    params_encoded = urllib.urlencode(params)
    return 'http://maps.googleapis.com/maps/api/geocode/json?%s' % params_encoded

def launch_rpc(feature):
    url = get_url(feature)   
    rpc = urlfetch.create_rpc()
    return urlfetch.make_fetch_call(rpc, url)

def lookup(features):
    """Return dict {'name': geocode} results for supplied list of feature names."""        
    results = apply(dict, [zip(features, ['' for x in features])])
    to_put = []
    for feature in features:
        geocode = Geocode.get_or_insert(feature)
        if geocode.results and geocode.results.has_key('google-geocode-api'):
            results[feature] = geocode
        else:
            results[feature] = (geocode, launch_rpc(feature))
    geocodes = {}
    for feature, val in results.iteritems():
        if isinstance(val, Geocode):
            geocodes[feature] = val.results
        else:
            geocode, rpc = val
            result = json.loads(rpc.get_result().content)            
            if not geocode.results:
                geocode.results = {'google-geocode-api': result}
            else:
                geocode.results['google-geocode-api'] = result
            geocodes[feature] = geocode.results
            to_put.append(geocode)
    ndb.put_multi(to_put)
    return geocodes

