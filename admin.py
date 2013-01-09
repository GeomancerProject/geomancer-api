import json
import pickle
import os
import webapp2
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from oauth2client.appengine import StorageByKeyName
from oauth2client.appengine import CredentialsModel
from oauth2client.client import OAuth2WebServerFlow

SCOPE = ('https://www.googleapis.com/auth/devstorage.read_write ' +
         'https://www.googleapis.com/auth/prediction')
USER_AGENT = 'geomancer-api/1.0'
SECRETS_FILE = 'client_secrets.json'

def parse_json_file(file):
	file = os.path.join(os.path.dirname(__file__), file)
	f = open(file, 'r')
	json_str = f.read()
	f.close()
	return json.loads(json_str)

class AuthHandler(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		credentials = StorageByKeyName(CredentialsModel, USER_AGENT, 'credentials').locked_get()
		if not credentials or credentials.invalid:
			if not user:
				self.redirect("/reset")
			secrets = parse_json_file(SECRETS_FILE)
			client_id = secrets['installed']['client_id']
			client_secret = secrets['installed']['client_secret']
			flow = OAuth2WebServerFlow(
				client_id=client_id,	
				client_secret=client_secret,
				scope=SCOPE,
				user_agent=USER_AGENT,
				access_type = 'offline',
				approval_prompt='force',
				redirect_uri=self.request.relative_url('/admin/oauth/callback'))
			authorize_url = flow.step1_get_authorize_url()#callback)
			memcache.set(user.user_id(), pickle.dumps(flow))
			self.redirect(authorize_url)

class CallbackHandler(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		flow = pickle.loads(memcache.get(user.user_id()))
		if flow:
			credentials = flow.step2_exchange(self.request.params)
			StorageByKeyName(CredentialsModel, USER_AGENT,
				'credentials').locked_put(credentials)
			self.redirect('/api/georef?q=berkeley')
		else:
			raise('unable to obtain OAuth 2.0 credentials')

class FlushHandler(webapp2.RequestHandler):
	def get(self):
		from geomancer.model import Cache, Locality
		from google.appengine.ext import ndb
		ndb.delete_multi(Cache.query().fetch(keys_only=True))
		ndb.delete_multi(Locality.query().fetch(keys_only=True))

handler = webapp2.WSGIApplication(
	[('/admin/oauth', AuthHandler),
	('/admin/oauth/callback', CallbackHandler),
	('/admin/cache/flush', FlushHandler)], 
	debug=True)
         
def main():
    run_wsgi_app(handler)

if __name__ == "__main__":
    main()