from geomancer.model import Locality
from google.appengine.ext import ndb

class LocParts(ndb.Model):
	results = ndb.JsonProperty(required=True)

def parts(name, loctype):
	"""Retutn parts dictionary from supplied locality name and type."""
	locparts = LocParts.get_by_id(Locality.normalize(name))
	if locparts:
		return locparts.results	
	# TODO
	return dict(features=['berkeley'])


