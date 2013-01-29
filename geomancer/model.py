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

"""Datastore models."""

import json
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

class Cache(polymodel.PolyModel):
	"""A simple Cache moodel."""
	results = ndb.JsonProperty()
	normalized_name = ndb.ComputedProperty(lambda x: x.key.id())	
	source = ndb.StringProperty()

	@classmethod
	def normalize_name(cls, name):
		"""Return normalized version of supplied name."""
		return ' '.join(name.lower().strip().split())

	@classmethod 
	def get_or_insert(cls, name, source=None):
		"""Get existing or create new model and return it."""
		id = '%s-%s' % (cls._class_name(), cls.normalize_name(name))
		return super(Cache, cls).get_or_insert(id, source=source)

	@classmethod
	def from_line(cls, source, line):
		name, payload = line.split('\t')
		geocode = cls.get_or_insert(name)
		if not geocode.results:
			geocode.results = {source: json.loads(payload)}
		else:
			geocode.results[source] = json.loads(payload)
		return geocode

	@classmethod
	def from_source(cls, source):
		return cls.query(cls.source==source).iter()

def _create_georef_csv(georef):
    """Return CSV representation for supplied Georef."""
    return '\t'.join(map(str, [georef.lon, georef.lat, georef.uncertainty]))

class Georef(ndb.Model):
	"""Models a georeference."""
	lat = ndb.FloatProperty(required=True, indexed=False)
	lon = ndb.FloatProperty(required=True, indexed=False)
	uncertainty = ndb.FloatProperty(required=True, indexed=False)
	bbox = ndb.FloatProperty(repeated=True, indexed=False) # GeoJSON bbox	
	csv = ndb.ComputedProperty(_create_georef_csv, indexed=False)
	geojson = ndb.JsonProperty()

	def _pre_put_hook(self):
		"""Set geojson property."""
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
		"""Return a new unsaved Georef model from supplied dictionary."""
		n = d['bounds']['northeast']['lat']
		e = d['bounds']['northeast']['lng']
		s = d['bounds']['southwest']['lat'] 
		w = d['bounds']['southwest']['lng']
		bbox = [w, s, e, n]
		return cls(lat=d['lat'], lon=d['lng'], uncertainty=d['uncertainty'], 
			bbox=bbox)

class Clause(ndb.Model):
	"""Models a locality name clause."""
	name = ndb.StringProperty(required=True)
	normalized_name = ndb.ComputedProperty(lambda x: x.key.id())
	interpreted_name = ndb.StringProperty()
	loctype = ndb.StringProperty()
	parts = ndb.JsonProperty()
	georefs = ndb.KeyProperty(kind=Georef, repeated=True)

	@classmethod
	def normalize_name(cls, name):
		"""Return normalized version of supplied name."""
		return ' '.join(name.lower().strip().split())

	@classmethod
	def get_by_id(cls, name):
		"""Return Clause for supplied clause name."""
		return super(Clause, cls).get_by_id(cls.normalize_name(name))

	@classmethod
	def get_or_insert(cls, name):
		"""Get or insert Clause."""
		id = cls.normalize_name(name)
		return super(Clause, cls).get_or_insert(id, name=name)

def _create_locality_csv(loc):
    """Return supplied Locality as a CSV string."""
    hdr = '\t'.join(['name', 'longitude', 'latitude', 'uncertainty'])
    lines = [hdr]
    for georef in loc.georefs:
    	lines.append('\t'.join([loc.name, georef.get().csv]))
    return '\n'.join(lines)

class Locality(ndb.Model): 
	"""Models a georeferenced locality clause."""
	name = ndb.StringProperty(required=True)
	normalized_name = ndb.ComputedProperty(lambda x: x.key.id())
	interpreted_name = ndb.StringProperty()
	clauses = ndb.KeyProperty(kind=Clause, repeated=True)
	georefs = ndb.KeyProperty(kind=Georef, repeated=True)	
	csv = ndb.ComputedProperty(_create_locality_csv, indexed=False)
	json = ndb.JsonProperty()

	def _pre_put_hook(self):
		"""Set json property."""
		self.json = dict(
			location=dict(name=self.name),
			georefs=[x.get().geojson for x in self.georefs])

	@classmethod
	def normalize_name(cls, name):
		"""Return normalized version of supplied name."""
		return ' '.join(name.lower().strip().split())

	@classmethod
	def get_by_id(cls, name):
		"""Return Clause identified by supplied name."""
		return super(Locality, cls).get_by_id(cls.normalized_name(name))

	@classmethod
	def get_or_insert(cls, name):
		"""Get or insert Clause."""
		id = cls.normalize_name(name)
		return super(Locality, cls).get_or_insert(id, name=name)