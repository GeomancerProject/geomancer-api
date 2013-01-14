import logging
import webapp2
from geomancer import predict, parse, geocode, error, util
from geomancer.model import Locality
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import CredentialsModel
from oauth2client.appengine import StorageByKeyName

def normalize(name):
    "Return the normalized version of supplied name."
    return name.lower().strip()

def georeference(name, credentials=None):
    name = normalize(name)
    loctype, scores = predict.loctype(name, credentials=credentials)
    logging.info('LOCTYPE %s\n' % loctype)
    parts = parse.parts(name, loctype)
    logging.info('PARTS_BEFORE_LOOKUP %s\n' % parts)
    if len(parts) == 0:
        return None
    parts['feature_geocodes'] = {}
    for feature in parts['features']:
        fg = geocode.lookup(normalize(feature))
        logging.info('FEATURE_GEOCODES for %s %s\n' % (feature, fg) )
        parts['feature_geocodes'][feature] = geocode.lookup(normalize(feature))
    georefs = error.get_georefs_from_parts(parts)
    logging.info('GEOREFS %s\n' % georefs)
    return Locality(id=Locality.normalize(name), name=name, loctype=loctype, 
        parts=parts, georefs=georefs)

def create_geojson(georef):
    "Return GeoJSON representation of georef dictionary."
    return {
        "feature": {                  
            "type": "Feature",
            "bbox": [-180.0, -90.0, 180.0, 90.0], # TODO
            "geometry": { 
                "type": "Point",  
                "coordinates": [float(georef['lng']), float(georef['lat'])]
            }
        },
        "uncertainty": float(georef['uncertainty'])
    }

def create_result(loc):
    "Return supplied Locality as a Geomancer result object."
    return dict(
        location=dict(
            original=loc.name,
            normalized=loc.parts['interpreted_loc'],
            type=loc.parts['locality_type']),
        georefs=map(create_geojson, loc.georefs))

class ApiHandler(webapp2.RequestHandler):
    def post(self):
        self.get()

    def get(self):
    	credentials = StorageByKeyName(CredentialsModel, 'geomancer-api/1.0', 
    		'credentials').locked_get()
    	if not credentials or credentials.invalid:
    		raise Exception('missing OAuth 2.0 credentials')
    	name = self.request.get('q')
        logging.info('NAME %s\n\n' % name)
    	loc = Locality.get_by_name(name)
    	logging.info('LOC %s\n\n' % loc)
    	if not loc or loc.georefs is None:
            loc = georeference(name, credentials)
            if loc:
                loc.put()
                response = util.dumps(create_result(loc))
            else:
                loc = dict(oops='Unable to georeference %s' % name)            
                response = util.dumps(loc)
    	self.response.out.write(response)

class StubHandler(webapp2.RequestHandler):
    STUB = {
      "locality":{
        "original":"Berkeley",
        "normalized":"berkeley"
      },
      "georefs":[
        {
          "feature":{                  
            "type": "Feature",
            "bbox": [-180.0, -90.0, 180.0, 90.0],
            "geometry": { 
              "type": "Point",  
              "coordinates": [100.0, 0.0] 
            }
          },
          "uncertainty": 100
        }
      ]
    }

    def post(self):
        self.get()

    def get(self):
        name = self.request.get('q')
        stub = self.STUB
        stub['locality']['original'] = name
        stub['locality']['normalized'] = name.lower().strip()
        self.response.out.write(util.dumps(stub))        

handler = webapp2.WSGIApplication([
    ('/api/georef', ApiHandler),
    ('/api/georef/stub', StubHandler)], debug=True)
         
def main():
    run_wsgi_app(handler)

if __name__ == "__main__":
    main()