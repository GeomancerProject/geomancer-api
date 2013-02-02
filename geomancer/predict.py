import httplib2
from apiclient.discovery import build
from geomancer.model import Cache

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

def loctype(name, creds, model='loctype-no-trs'):
	"Return [type, scores] for supplied locality name."
	loctype = Predict.get_or_insert(name)
	if loctype.results:
		return loctype.results
	tokens = [x.strip() for x in name.split()]
	if len(tokens) == 1:
		loctype.results = ['f',{u'f': 0.9, u'p': 0.10}]
		loctype.put()
		return loctype.results
	payload = {"input": {"csvInstance": [name]}}
	http = creds.authorize(httplib2.Http())
	service = build('prediction', 'v1.5', http=http)
	resp = service.trainedmodels().predict(id=model, body=payload).execute()
	prediction = resp['outputLabel']
	scores = format(resp['outputMulti'])
	loctype.results = [prediction, scores]
	loctype.source = 'google-prediction-api'
	loctype.put()
	return loctype.results


