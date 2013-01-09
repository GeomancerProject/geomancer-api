import httplib2
from apiclient.discovery import build
from geomancer.model import Cache
from google.appengine.ext import ndb

class Predict(Cache):
	pass

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

def loctype(name, credentials=None, model='loctype'):
	"Retutn [type, scores] for supplied locality name."
	loctype = Predict.get_or_insert(name)
	if loctype.results:
		return loctype.results
	payload = {"input": {"csvInstance": [name]}}
	http = credentials.authorize(httplib2.Http())
	service = build('prediction', 'v1.5', http=http)
	resp = service.trainedmodels().predict(id=model, body=payload).execute()
	prediction = resp['outputLabel']
	scores = format(resp['outputMulti'])
	loctype.results = [prediction, scores]
	loctype.put()
	return loctype.results


