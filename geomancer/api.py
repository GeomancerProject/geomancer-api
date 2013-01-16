from geomancer import cdb
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
    parts = parse.parts(name, loctype)
    if len(parts) == 0:
        return dict(status='Failed', locality=name, 
            why='Unsupported loctype %s' % loctype)
    parts['feature_geocodes'] = {}
    for feature in parts['features']:
        fg = geocode.lookup(normalize(feature))
        logging.info('FEATURE_GEOCODES for %s %s\n' % (feature, fg) )
        parts['feature_geocodes'][feature] = fg
    georefs = error.get_georefs_from_parts(parts)
    if len(georefs) == 0:
        return dict(status='Failed', locality=name, 
            why='No georeferences for loctype %s' % loctype)
    loc = Locality(id=Locality.normalize(name), name=name, loctype=loctype, 
        parts=parts, georefs=georefs)
    loc.put()
    return loc

def create_csv(georef):
    "Return georef dict as CSV."
    return '%s,%s,%s' % (georef['lng'], georef['lat'], georef['uncertainty'])

def create_geojson(georef):
    "Return GeoJSON representation of georef dictionary."
    n = georef['bounds']['northeast']['lat']
    e = georef['bounds']['northeast']['lng']
    s = georef['bounds']['southwest']['lat'] 
    w = georef['bounds']['southwest']['lng']
    logging.info('GEOREF for GEOJSON %s\n' % georef )
    return {
        "feature": {                  
            "type": "Feature",
            "bbox": [w, s, e, n],
            "geometry": { 
                "type": "Point",  
                "coordinates": [georef['lng'], georef['lat']]
            }
        },
        "uncertainty": georef['uncertainty']
    }

def create_csv_result(loc):
    "Return supplied Locality as a CSV string."
    hdr = 'loc_original,loc_normalized,loc_type,longitude,latitude,uncertainty'
    lines = [hdr]
    for georef in loc.georefs:
        lines.append('%s,%s,%s,%s' %(loc.name, loc.parts['interpreted_loc'],
            loc.parts['locality_type'], create_csv(georef)))
    return '\n'.join(lines)

def create_geojson_result(loc):
    "Return supplied Locality as a Geomancer result object."
    return dict(
        location=dict(
            original=loc.name,
            normalized=loc.parts['interpreted_loc'],
            type=loc.parts['locality_type']),
        georefs=map(create_geojson, loc.georefs))

def create_results(loc, format, user=None, api_key=None, table=None):
    "Return results for Locality in format."
    if format == 'csv':
        return create_csv_result(loc)
    elif format == 'cartodb':
        return cdb.save_results(create_csv_result(loc), user, api_key, table)
    else:
        return util.dumps(create_geojson_result(loc))

class ApiHandler(webapp2.RequestHandler):
    def post(self):
        self.get()

    def get(self):
    	credentials = StorageByKeyName(CredentialsModel, 'geomancer-api/1.0', 
    		'credentials').locked_get()
    	if not credentials or credentials.invalid:
    		raise Exception('missing OAuth 2.0 credentials')
    	name = self.request.get('q')
        format = self.request.get('f', 'geojson')
        user = self.request.get('user', None)
        api_key = self.request.get('api_key', None)
        table = self.request.get('table', None)
    	loc = Locality.get_by_name(name)
    	if not loc or loc.georefs is None:
            loc = georeference(name, credentials)
            if type(loc) == dict:
                results = util.dumps(loc)
            else:
                results = create_results(loc, format, user=user, 
                    api_key=api_key, table=table)
        else:
            results = create_results(loc, format, user=user, 
                    api_key=api_key, table=table)

        if format == 'csv':
            self.response.headers['Content-type'] = 'text/csv'
        elif format == 'cartodb':
            logging.info('RESULTS %s' % results)
            self.redirect(str(results))
            return

    	self.response.out.write(results)

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