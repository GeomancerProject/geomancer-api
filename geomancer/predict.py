import httplib2
from apiclient.discovery import build
from google.appengine.ext import ndb

class LocType(ndb.Model):
	results = ndb.JsonProperty(required=True)

	@classmethod
	def get_by_name(cls, name):
		return cls.get_by_id(cls.normalize(name))

	@classmethod
	def normalize(cls, name):
		"Return the normalized version of supplied locality name."
		return name.lower().strip()

def format(jsonscores):
	scores = {}
	for pair in jsonscores:
		for key, value in pair.iteritems():
			if key == 'label':
				label = value
			elif key == 'score':
				score = value
		scores[label] = score
	return scores

def loctype(name, credentials=None, model='biogeomancer/locs.csv'):
	"Retutn [type, scores] for supplied locality name."
	loctype = LocType.get_by_name(name)
	if loctype:
		return loctype.results
	if not credentials:
		return ['f', []]		
	payload = {"input": {"csvInstance": [name]}}
	http = credentials.authorize(httplib2.Http())
	service = build('prediction', 'v1.4', http=http)
	resp = service.trainedmodels().predict(id=model,body=payload).execute()
	prediction = resp['outputLabel']
	scores = format(resp['outputMulti'])
	results = [prediction, scores]
	LocType(id=LocType.normalize(name), results=results).put()
	return results


