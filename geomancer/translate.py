from apiclient.discovery import build
from geomancer.model import Cache
import os
import logging

f = open(os.path.join(os.path.dirname(__file__), 'translate_key'))
key = f.read()
f.close()
service = build('translate', 'v2', developerKey=key)

class Translation(Cache):
	pass

def english(q, source):
	translation = Translation.get_or_insert(q)
	if translation.results:
		return translation.results
	request = service.translations().list(source=source, target='en', q=[q])
	result = request.execute()
	logging.info("Translated %s in %s to %s" % (q, source, result))
	translation.results = result.get('translations')[0].get('translatedText')
	translation.put()
	return translation.results