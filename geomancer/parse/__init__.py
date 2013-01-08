from geomancer.model import Locality
from geomancer.parse import core
from google.appengine.ext import ndb

class LocParts(ndb.Model):
	results = ndb.JsonProperty()

def parts(name, loctype):
	"""Retutn parts dictionary from supplied locality name and type."""
	locparts = LocParts.get_or_insert(Locality.normalize(name))
	if locparts.results:
		return locparts.results	
	locparts.results = core.parse_loc(name, loctype)
	locparts.put()
	return locparts.results
