#!/usr/bin/env python

from optparse import OptionParser
import urllib
import httplib2
import logging

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)    
    
    parser = OptionParser()
    parser.add_option("-c", "--cartodb", dest="cdb",
                      help="CartoDB triple: user, table, api_key",
                      default=None)
    parser.add_option("-e", "--email", dest="email",
                      help="Email to ping when job finishes.",
                      default=None)
    parser.add_option("-u", "--url", dest="url",
                      help="URL endpoint for bulkload API.",
                      default=None)
    parser.add_option("-f", "--file", dest="file",
                      help="CSV file of data.",
                      default=None)
    parser.add_option("-l", "--lang", dest="lang",
                      help="Language code for file data.",
                      default=None)    
    (options, args) = parser.parse_args()

    client = httplib2.Http()
    data = open(options.file).read()
    body = urllib.urlencode(dict(data=data, cdb=options.cdb, 
    	email=options.email, lang=options.lang))
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    resp, content = client.request(options.url, "POST", body=body, 
    	headers=headers)
    