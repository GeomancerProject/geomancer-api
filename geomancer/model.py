from google.appengine.ext import ndb

class Locality(ndb.Model):
	"Models a georeferenced locality."
	name = ndb.StringProperty()
	loctype = ndb.StringProperty()
	parts = ndb.JsonProperty()
	georefs = ndb.JsonProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)

	@classmethod
	def get_by_name(cls, name):
		"Return Locality from supplied name or None if it doesn't exits."
		return cls.get_by_id(cls.normalize(name))

	@classmethod
	def normalize(cls, locname):
		"Return the normalized version of supplied locality name."
		return locname.lower().strip()
