import json
import urllib
from google.appengine.ext import ndb
from google.appengine.api import urlfetch

class FeatureGeocode(ndb.Model):
    results = ndb.JsonProperty(required=True)

    @classmethod
    def get_by_feature(cls, feature):
        """Return FeatureGeocode from supplied feature name or None if it 
        doesn't exist."""
        return cls.get_by_id(cls.normalize(feature))

    @classmethod
    def normalize(cls, feature):
        "Return the normalized version of supplied feature name."
        return feature.lower().strip()

def lookup(feature):
    """Return Google Geocode API results for supplied feature name."""    
    geocode = FeatureGeocode.get_by_feature(feature)
    if geocode:
        return geocode.results
    params = urllib.urlencode([('address', feature), ('sensor', 'false')])
    url = 'http://maps.googleapis.com/maps/api/geocode/json?%s' % params
    results = json.loads(urlfetch.fetch(url).content)
    FeatureGeocode(id=FeatureGeocode.normalize(feature), results=results).put()
    return results