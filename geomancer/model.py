from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

class Cache(polymodel.PolyModel):
	results = ndb.JsonProperty()
	normalized_name = ndb.ComputedProperty(lambda x: x.key.id())

	@classmethod
	def normalize_name(cls, name):
		"Return normalized version of supplied name."
		return ' '.join(name.lower().strip().split())

	@classmethod 
	def get_or_insert(cls, name):	
		id = '%s-%s' % (cls._class_name(), cls.normalize_name(name))
		return super(Cache, cls).get_or_insert(id)

def _create_georef_csv(georef):
    "Return CSV representation from supplied Georef."
    return ','.join(map(str, [georef.lon, georef.lat, georef.uncertainty]))

class Georef(ndb.Model):
	lat = ndb.FloatProperty(required=True)
	lon = ndb.FloatProperty(required=True)
	uncertainty = ndb.FloatProperty(required=True)
	bbox = ndb.FloatProperty(repeated=True) # GeoJSON bbox	
	csv = ndb.ComputedProperty(_create_georef_csv, indexed=False)
	geojson = ndb.JsonProperty()

	def _pre_put_hook(self):
		"Set geojson property."
		w, s, e, n = self.bbox
		self.geojson = {
		    "feature": {                  
                "type": "Feature",
                "bbox": [w, s, e, n],
                "geometry": { 
                    "type": "Point",  
                    "coordinates": [self.lon, self.lat]
                }
            },
            "uncertainty": self.uncertainty
        }

	@classmethod
	def from_dict(cls, d):
		"Return a new unsaved Georef model from supplied dictionary."
		n = d['bounds']['northeast']['lat']
		e = d['bounds']['northeast']['lng']
		s = d['bounds']['southwest']['lat'] 
		w = d['bounds']['southwest']['lng']
		bbox = [w, s, e, n]
		return cls(lat=d['lat'], lon=d['lng'], uncertainty=d['uncertainty'], 
			bbox=bbox)

class Clause(ndb.Model): # id is name.lower().strip()
	name = ndb.StringProperty(required=True)
	normalized_name = ndb.ComputedProperty(lambda x: x.key.id())
	interpreted_name = ndb.StringProperty()
	loctype = ndb.StringProperty()
	parts = ndb.JsonProperty()
	georefs = ndb.KeyProperty(kind=Georef, repeated=True)

	@classmethod
	def normalize_name(cls, name):
		"Return normalized version of supplied name."
		return ' '.join(name.lower().strip().split())

	@classmethod
	def get_by_id(cls, name):
		"Return Wallet identified by supplied person and shell."
		return super(Clause, cls).get_by_id(cls.normalized_name(name))

	@classmethod
	def get_or_insert(cls, name):
		"Get or insert Clause."
		id = cls.normalize_name(name)
		return super(Clause, cls).get_or_insert(id, name=name)

def _create_locality_csv(loc):
    "Return supplied Locality as a CSV string."
    hdr = 'name,longitude,latitude,uncertainty'
    lines = [hdr]
    for georef in loc.georefs:
        lines.append(','.join([loc.name, georef.get().csv]))
    return '\n'.join(lines)

class Locality(ndb.Model): # id is name.lower().strip()
	"Models a georeferenced locality clause."
	name = ndb.StringProperty(required=True)
	normalized_name = ndb.ComputedProperty(lambda x: x.key.id())
	interpreted_name = ndb.StringProperty()
	clauses = ndb.KeyProperty(kind=Clause, repeated=True)
	georefs = ndb.KeyProperty(kind=Georef, repeated=True)	
	csv = ndb.ComputedProperty(_create_locality_csv)
	json = ndb.JsonProperty()

	def _pre_put_hook(self):
		self.json = dict(
			location=dict(name=self.name),
			georefs=[x.get().geojson for x in self.georefs])

	@classmethod
	def normalize_name(cls, name):
		"Return normalized version of supplied name."
		return ' '.join(name.lower().strip().split())

	@classmethod
	def get_by_id(cls, name):
		"Return Wallet identified by supplied person and shell."
		return super(Locality, cls).get_by_id(cls.normalized_name(name))

	@classmethod
	def get_or_insert(cls, name):
		"Get or insert Clause."
		id = cls.normalize_name(name)
		return super(Locality, cls).get_or_insert(id, name=name)