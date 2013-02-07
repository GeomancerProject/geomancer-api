from geomancer import cdb as cartodb
import datetime
import logging
import json
import webapp2
import os
from functools import partial
from geomancer import translate
from geomancer import predict, parse, geocode, util, core
from geomancer.model import Locality, Georef, Clause
from geomancer.geocode import Geocode
from google.appengine.api import mail
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import CredentialsModel
from oauth2client.appengine import StorageByKeyName

def normalize(name):
    "Return the normalized version of supplied name."
    return name.lower().strip()

def georef(creds, lang, name):
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
    if not parts or len(parts) == 0:
        return None
    features = parts['features']
    if lang:        
        features_trans = map(partial(translate.get, 'en', lang), features)
        geocodes = geocode.lookup(map(normalize, features_trans))
        geocodes = apply(dict, [zip(features, geocodes.values())])
    else:
        geocodes = geocode.lookup(map(normalize, features))
    parts['feature_geocodes'] = geocodes
    georefs = map(Georef.from_dict, core.get_georefs_from_parts(parts))
    if len(georefs) == 0:
        return None
    ndb.put_multi(georefs)
    clause.interpreted_name = parts['interpreted_loc']
    clause.loctype = loctype
    clause.parts = parts
    clause.georefs = [x.key for x in georefs]
    return clause

def process_loc(creds, lang, loc_name):
    if lang:
        loc_name = translate.get(lang, 'en', loc_name)
    loc = Locality.get_or_insert(loc_name)
    if not loc.georefs:            
        clause_names = core.clauses_from_locality(loc_name)
        clauses = [x for x in map(partial(georef, creds, lang), clause_names) \
                   if x]
        ndb.put_multi(clauses)
        loc.interpreted_name = ';'.join([x.interpreted_name for x in clauses])        
        loc.georefs = core.loc_georefs(clauses) or []
        loc.clauses = [x.key for x in clauses]
        loc.put()
    return loc

def get_creds():
    creds = StorageByKeyName(CredentialsModel, 'geomancer-api/1.0', 
        'credentials').locked_get()
    if not creds or creds.invalid:
        raise Exception('missing OAuth 2.0 credentials')
    return creds

def validate_user(handler):
    key = open(os.path.join(os.path.dirname(__file__), 'tester.key')).read()
    if handler.request.get('k') != key:
        handler.response.out.write('Private beta (contact @eightysteele or @tucotuco for access)')
        handler.response.set_status(405)
        return False
    return True

class ApiHandler(webapp2.RequestHandler):
    
    def post(self):
        self.get()

    def get(self):
        if not validate_user(self):
            return
        creds = get_creds()
        q, format, cdb, lang, cb = map(self.request.get, ['q', 'f', 'cdb', 'l', 'cb'])        
        loc = process_loc(creds, lang, q)
        if format == 'csv':
            self.response.out.headers['Content-Type'] = 'text/csv'
            result = loc.csv
        elif format == 'verbose':
            self.response.out.headers['Content-Type'] = 'application/json'
            result = util.dumps(loc)        
        else: 
            self.response.out.headers['Content-Type'] = 'application/json'
            result = json.dumps(loc.json)
        if cb:
            self.response.out.headers['Content-Type'] = 'application/javascript'
            result = '%s(%s);' % (cb, result)  
        if cdb:
            user, table, apikey = cdb.split(',')
            link = cartodb.save_results(loc.csv, user, table, apikey)
            result = loc.json
            loc.json['cartodb_link'] = link
            result = json.dumps(result)
        self.response.headers['charset'] = 'utf-8'
        self.response.out.write(result)

class ComponentHandler(webapp2.RequestHandler):
    def get(self):
        self.post()

    def post(self): 
        if not validate_user(self):
            return
        q, component = map(self.request.get, ['q', 'c'])
        if component == 'geocode':
            results = geocode.lookup(q.split(','))
        if component == 'translate':
            source, target, q = q.split(',')
            results = translate.get(source, target, q)
        elif component == 'predict':
            results = predict.loctype(q, get_creds())
        elif component == 'parts':
            name, loctype = q.split(',')
            results = parse.parts(name, loctype)
        elif component == 'clauses':
            results = [core.clauses_from_locality(x) for x in q.split(',')]
        self.response.out.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(results))

class BulkJob(ndb.Model):
    data = ndb.TextProperty(required=True)
    cdb = ndb.StringProperty(required=True) # csv: user,table,api_key
    email = ndb.StringProperty(required=True)
    lang = ndb.StringProperty(default=None)
    created = ndb.DateTimeProperty(auto_now_add=True)
    finished = ndb.DateTimeProperty(default=None)

class BulkApi(webapp2.RequestHandler):
    def get(self):
        self.post()

    def post(self): 
        data, cdb, email, lang = map(self.request.get, 
            ['data', 'cdb', 'email', 'lang'])
        job = BulkJob(data=data, cdb=cdb, email=email, lang=lang).put()
        params = dict(job=job.urlsafe())
        taskqueue.add(url='/api/georef/bulkworker', queue_name='bulk', 
            params=params)            

class BulkWorker(webapp2.RequestHandler):
    """Idempotent handler for notifying a person of an event."""
    def post(self): 
        if not validate_user(self):
            return
        job = ndb.Key(urlsafe=self.request.get('job')).get()
        creds = get_creds()
        if job.finished:
            return
        user, table, api_key = job.cdb.split(',')
        lines = iter(job.data.splitlines())        
        for loc in map(partial(process_loc, creds, job.lang), lines):
            cartodb.save_results(loc.csv, user, table, api_key)
        job.finished = datetime.datetime.now()
        job.put()
        url = 'http://%s.cartodb.com/tables/%s' % (user, table)
        message = mail.EmailMessage(
            sender='noreply@geomancer-api.appspot.com', to=job.email, 
            subject='Your Geomancer Job is complete!', body=url)
        message.send()

class CacheWorker(webapp2.RequestHandler):
    """Bulkloads Cache models to datastore."""
    def post(self):
        data, source, kind = map(self.request.get, ['data', 'source', 'kind'])
        if kind == 'Geocode':
            models = map(partial(Geocode.from_line, source, kind), data.splitlines())
        ndb.put_multi(models)
        self.response.out.status = 201

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
    ('/api', ComponentHandler),    
    ('/api/georef/stub', StubHandler),
    ('/api/cache/bulk', CacheWorker),
    ('/api/georef/bulk', BulkApi),
    ('/api/georef/bulkworker', BulkWorker)], debug=True)
         
def main():
    run_wsgi_app(handler)

if __name__ == "__main__":
    main()