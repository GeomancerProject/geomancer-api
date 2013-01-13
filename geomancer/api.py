import webapp2
import logging
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
#    logging.info('GEOREF %s' % name)
    loctype, scores = predict.loctype(name, credentials=credentials)
#    logging.info('LOCTYPE %s' % loctype)
    parts = parse.parts(name, loctype)
    logging.info('PARTS_BEFORE_LOOKUP %s' % parts)
    if len(parts) == 0:
        return None
    parts['feature_geocodes'] = {}
    for feature in parts['features']:
        fg = geocode.lookup(normalize(feature))
        logging.info('FEATURE_GEOCODES for %s %s' % (feature, fg) )
        parts['feature_geocodes'][feature] = geocode.lookup(normalize(feature))
#    logging.info('PARTS-AFTER_LOOKUP %s' % parts)
    georefs = error.get_georefs_from_parts(parts)
    logging.info('GEOREFS %s' % georefs)
    return Locality(id=Locality.normalize(name), name=name, loctype=loctype, 
        parts=parts, georefs=georefs)

class ApiHandler(webapp2.RequestHandler):
    def post(self):
        self.get()

    def get(self):
    	credentials = StorageByKeyName(CredentialsModel, 'geomancer-api/1.0', 
    		'credentials').locked_get()
    	if not credentials or credentials.invalid:
    		raise Exception('missing OAuth 2.0 credentials')
    	name = self.request.get('q')
        logging.info('NAME %s' % name)
    	loc = Locality.get_by_name(name)
    	logging.info('LOC %s' % loc)
    	if not loc or loc.georefs is None:
            loc = georeference(name, credentials)
            if loc:
                loc.put()
            else:
                loc = dict(oops='Unable to georeference %s' % name)
    	self.response.out.write(util.dumps(loc))

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