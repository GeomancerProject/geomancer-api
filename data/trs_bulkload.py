#!/usr/bin/env python

"""Bulkload TRS data from file to Cache model in datastore."""

from collections import defaultdict
from optparse import OptionParser
import itertools
import time
import urllib
import httplib2
import json
import sys
import os
import logging

def partition(iterable, size):
    """Generates partitions of supplied iterable of length size."""
    it = iter(iterable)
    item = list(itertools.islice(it, size))
    while item:
        yield item
        item = list(itertools.islice(it, size))

def bulkload(path, url):
    """Bulkload file at supplied path to url endpoint."""
    logging.info('Bulkloading %s to %s' % (path, url))
    client = httplib2.Http()
    retries = 5
    retry_count = 0
    backoff = 1
    for p in partition(open(out_name, 'r').read().splitlines(), 1000):
        logging.info('Processing partition...')
        lines = '\n'.join(p)
        params = dict(data=lines, kind='Geocode')
        body = urllib.urlencode(params)
        headers = {'Content-type': 'application/x-www-form-urlencoded'}         
        resp, content = client.request(url, "POST", body=body, headers=headers)
        while resp.status != 201 and retry_count < retries:
            logging.info('BACKOFF %s of %s (%s)' % (retry_count, retries, content))
            backoff *= 2
            time.sleep(backoff)
            resp, content = client.request(url, "POST", body=body, 
                headers=headers)
            retry_count += 1
        if retry_count == retries:
            logging.info("Retries failed, goodbye!")
            sys.exit()
        backoff = 1
        retry_count = 0
        time.sleep(backoff)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)        
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="file",
                      help="CSV file of data.",
                      default=None)
    parser.add_option("-u", "--url", dest="url",
                      help="URL endpoint for bulkload API.",
                      default=None)    
    (options, args) = parser.parse_args()
    data = defaultdict(list)    
    logging.info("Processing %s into multimap of unique names to geocodes." % options.file)
    for line in open(options.file, 'r').read().splitlines():
    	i = line.find('{')    	
    	name = line[0:i].replace(',','').strip().lower()
    	geocode = line[i:]      
        data[name].append(geocode)
    out_name = '%s_multimap.csv' % (os.path.splitext(options.file)[0])
    out = open(out_name, 'w')
    logging.info("Writing results to %s." % out_name)
    for name,geocodes in data.iteritems():
    	out.write('%s\t%s\n' % (name, json.dumps(geocodes)))
    out.flush()
    out.close()
    bulkload(out_name, options.url)