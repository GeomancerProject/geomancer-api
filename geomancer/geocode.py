import json
import urllib
from geomancer.model import Cache
from google.appengine.ext import ndb
from google.appengine.api import urlfetch

class Geocode(Cache):
    pass

def lookup(feature):
    """Return Google Geocode API results for supplied feature name."""    
    geocode = Geocode.get_or_insert(feature)
    if geocode.results:
        return geocode.results
    params = urllib.urlencode([('address', feature), ('sensor', 'false')])
    url = 'http://maps.googleapis.com/maps/api/geocode/json?%s' % params
    geocode.results = json.loads(urlfetch.fetch(url).content)
    geocode.put()
    return geocode.results