import webapp2
import logging
from geomancer import predict, parse, geocode, error, util
from geomancer.model import Locality
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import CredentialsModel
from oauth2client.appengine import StorageByKeyName

def georeference(name, credentials=None):
    loctype, scores = predict.loctype(name, credentials=credentials)
    parts = parse.parts(name, loctype)
    if len(parts) == 0:
        return None
    parts['geocodes'] = {}
    for feature in parts['features']:
        parts['geocodes'][feature] = geocode.lookup(feature)
    georefs = error.calculate(parts)
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