from geomancer.model import Cache
from geomancer.parse import core

class Parts(Cache):
	pass

def parts(name, loctype):
	"""Retutn parts dictionary from supplied locality name and type."""
	parts = Parts.get_or_insert(name)
	if parts.results:
		return parts.results	
	parts.results = core.parse_loc(name, loctype)
	parts.put()
	return parts.results
