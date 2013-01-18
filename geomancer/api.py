from geomancer import cdb as cartodb
import logging
import json
import webapp2
from functools import partial
from geomancer import predict, parse, geocode, util, core
from geomancer.model import Locality, Georef, Clause
from google.appengine.ext import ndb
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import CredentialsModel
from oauth2client.appengine import StorageByKeyName

def normalize(name):
    "Return the normalized version of supplied name."
    return name.lower().strip()

def georef(creds, name):
    """Return a georeferenced Clause model from supplied clause name. The Clause
    will be populated with name, normalized_name, interpreted_name, loctype, parts,
    and georefs but it will not be saved. This is an optimization so that multiple
    clauses can be saved using ndb.put_multi() by the caller. The Clause georefs 
    will be saved.
    """
    clause = Clause.get_or_insert(name)
    if clause.georefs:
        return clause
    loctype, scores = predict.loctype(name, creds)
    parts = parse.parts(name, loctype)
    if len(parts) == 0:
        return None
    parts['feature_geocodes'] = {}
    for feature in parts['features']:
        parts['feature_geocodes'][feature] = geocode.lookup(normalize(feature))
    georefs = map(Georef.from_dict, core.get_georefs_from_parts(parts))
    if len(georefs) == 0:
        return None
    ndb.put_multi(georefs)
    clause.interpreted_name = parts['interpreted_loc']
    clause.loctype = loctype
    clause.parts = parts
    clause.georefs = [x.key for x in georefs]
    return clause

class ApiHandler(webapp2.RequestHandler):
    def _get_creds(self):
        creds = StorageByKeyName(CredentialsModel, 'geomancer-api/1.0', 
            'credentials').locked_get()
        if not creds or creds.invalid:
            raise Exception('missing OAuth 2.0 credentials')
        return creds

    def post(self):
        self.get()

    def get(self):
        creds = self._get_creds()
    	loc_name = self.request.get('q')
        format = self.request.get('f', 'json')
        cdb = self.request.get('cdb')
        loc = Locality.get_or_insert(loc_name)
        if not loc.georefs:            
            clause_names = core.clauses_from_locality(loc_name)
            clauses = [x for x in map(partial(georef, creds), clause_names) if x]
            ndb.put_multi(clauses)
            loc.interpreted_name = ';'.join([x.interpreted_name for x in clauses])        
            loc.georefs = core.loc_georefs(clauses)
            loc.clauses = [x.key for x in clauses]
            loc.put()
        if cdb:
            user, table, api_key = cdb.split(',')
            cartodb.save_results(loc.csv, user, table, api_key)
            return
        elif format == 'json':
            self.response.out.headers['Content-Type'] = 'application/json'
            result = json.dumps(loc.json)
        elif format == 'csv':
            self.response.out.headers['Content-Type'] = 'text/csv'
            result = loc.csv
        elif format == 'all':
            self.response.out.headers['Content-Type'] = 'application/json'
            result = util.dumps(loc)        
    	self.response.out.write(result)

class StubHandler(webapp2.RequestHandler):
    STUB = {
      "locality":{
        "original":"Berkeley",
        "normalized":"berkeley"
      },
      "georefs":[
        {
          "feadture":{                  
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