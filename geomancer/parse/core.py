#!/usr/bin/env python

# Copyright 2011 The Regents of the University of California 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "John Wieczorek (gtuco.btuco@gmail.com)"
__copyright__ = "Copyright 2011 The Regents of the University of California"
__contributors__ = ["Aaron Steele (eightysteele@gmail.com)"]

"""This module provides core functions and classes for georeferencing"""

import math
import logging
import simplejson

from constants import DistanceUnits
#from constants import Datums
from constants import Headings
from bb import *
from point import *

# Geomancer modules
from cache import Cache
from utils import UnicodeDictReader, UnicodeDictWriter, CredentialsPrompt

# Standard Python modules
#import httplib2
import logging
import optparse
import simplejson
import sys
import urllib
import yaml

class Locality(object):
    """Class representing a sub-locality."""
    
    @classmethod
    def create_muti(cls, location):
        """Return list of Locality objects by splitting location on ',' and ';'."""
        return [Locality(name.strip()) for name in set(reduce(            
                    lambda x,y: x+y, 
                    [x.split(';') for x in location.split(',')]))]

    def __init__(self, name):
        self.name = name
        self.type = None
        self.type_scores = None
        self.parts = {}
        self.georefs = []
    
    def __repr__(self):
        return str(self.__dict__)
    
class Geomancer(object):
    def __init__(self, predictor, geocoder, creds=None, cache_remote_host=None):
        self.predictor = predictor
        self.geocoder = geocoder
        Cache.config(creds=creds, remote_host=cache_remote_host)        

    def georef(self, location):
        """Georeferences a location."""
        localities = Locality.create_muti(location)
        logging.info('Georeferencing "%s" with sub-localities %s' % (location, [x.name for x in localities]))
        localities_predicted = self.predict(localities)
        localities_parsed = self.parse(localities_predicted)
        localities_geocoded = self.geocode(localities_parsed)
        localities_calculated, georefs = self.calculate(localities_geocoded)
        return (localities_geocoded, georefs)

    def predict(self, localities):
        """Predict locality type for each locality in a list."""
        for loc in localities:
            logging.info('Predicting locality type for "%s"' % loc.name)
            key = 'loctype-%s' % loc.name
            prediction = Cache.get(key)
            if not prediction:
                loctype, scores = self.predictor.get_type(loc.name)
                prediction = dict(locname=loc.name, loctype=loctype, scores=scores)
                Cache.put(key, prediction)
            loc.type = prediction['loctype']
            loc.type_scores = prediction['scores']
            logging.info('Predicted "%s" for "%s"' % (loc.type, loc.name))
        return localities

    def parse(self, localities):
        for loc in localities:
            logging.info('Parsing "%s" based on locality type "%s"' % (loc.name, loc.type))
            loc.parts = parse_loc(loc.name, loc.type)
            logging.info('Parsed features "%s"' % list(loc.parts['features']))
        return localities

    def geocode(self, localities):
        for loc in localities:
            loc.feature_geocodes = {}
            loc.parts['feature_geocodes'] = {}
            for feature in loc.parts['features']:              
                logging.info('Geocoding feature "%s"' % feature)  
                key = 'geocode-%s' % feature
                geocode = Cache.get(key)
                if not geocode:
                    geocode = self.geocoder.geocode(feature)
                    Cache.put(key, geocode)
                loc.parts['feature_geocodes'][feature] = geocode 
                logging.info('Geocoded feature "%s"' % feature)
        return localities

    def calculate(self, localities):
        georefs = loc_georefs(localities)
        return (localities, georefs)

def loc_georefs(localities):
    """localities is a list of Locality."""
    georef_lists=[]
    for loc in localities:
        georefs =  subloc_georefs(loc)
        # TODO: Decide what to do if any sublocality returns no georefs. For now, ignore that locality.
        # Minimally, if we do this, we have to change the interpreted locality.
        if len(georefs) > 0:
            loc.georefs = georefs
            georef_lists.append(georefs)
    ''' Now we have a list of lists of georefs, and we need to find intersecting combos.'''
    if len(georef_lists) == 0:
        return None
    results=georef_lists.pop()
    while len(georef_lists) > 0:
        next_georefs = georef_lists.pop()
        for result in results:
            new_results=[]
            for next_georef in next_georefs:
                new_result=result.intersection(next_georef)
                if new_result is not None:
                    new_results.append(new_result)
        results = new_results
    return results

def subloc_georefs(loc):
    if not loc.parts.has_key('feature_geocodes'):
        return None
    geocodes = loc.parts['feature_geocodes']
    if len(geocodes) == 0:
        return None
    loctype = loc.type
    georefs=[]
    for feature, geocode in geocodes.iteritems():
        geocodes = GeocodeResultParser.get_feature_geoms(feature, geocode)
        if geocodes is not None:
            for g in geocodes:
                if loctype == 'f':
                    bb = GeometryParser.get_bb(g)
                    georefs.append(bb)
                elif loctype == 'foh':
                    bb = GeometryParser.get_bb(g)
                    offset = loc.parts['offset_value']
                    offsetunit = loc.parts['offset_unit']
                    heading = loc.parts['heading'] 
                    new_bb = foh_error_bb(bb, offset, offsetunit, heading)
                    georefs.append(new_bb)
    return georefs

def unitDictionary(tokens):
    units = {}
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            ti = tokens[i]
            ti1 = tokens[i+1]
            unit = get_unit('%s%s' % (tokens[i].replace('.','').strip(), tokens[i+1].replace('.','').strip() ) )
            if unit is not None:
                units[i] = {'unit':unit.name, 'endtoken':i+1}
                i+=1
                break
        unit = get_unit(tokens[i].replace('.','').strip())
        if unit is not None: 
            units[i] = {'unit':unit.name, 'endtoken':i}
        i+=1
    return units
    
def headingDictionary(tokens):
    headings = {}
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            ti = tokens[i]
            ti1 = tokens[i+1]
            heading = get_heading('%s%s' % (tokens[i].replace('.','').strip(), tokens[i+1].replace('.','').strip() ) )
            if heading is not None:
                headings[i] = {'heading':heading.name, 'endtoken':i+1}
                i+=1
                break
        heading = get_heading(tokens[i].replace('.','').strip())
        if heading is not None: 
            headings[i] = {'heading':heading.name, 'endtoken':i}
        i+=1
    return headings
    
#def unitList(tokens):
#    units = []
#    i = 0
#    while i < len(tokens):
#        if i < len(tokens) - 1:
#            ti = tokens[i]
#            ti1 = tokens[i+1]
#            unit = get_unit('%s%s' % (tokens[i].replace('.','').strip(), tokens[i+1].replace('.','').strip() ) )
#            if unit is not None:
#                units.append( {'unit':unit.name, 'endtoken':i+1} )
#                i+=1
#                break
#        unit = get_unit(tokens[i].replace('.','').strip())
#        if unit is not None: 
#            units.append( {'unit':unit.name, 'endtoken':i} )
#        i+=1
#    return units
    
def findUnits(tokens):
    # Don't do anything to change tokens.
    # units: list of tuples of form
    # (unit index in tokens, unit_name, number of tokens comprising unit)
    units = []
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            unit = get_unit('%s%s' % (tokens[i].replace('.','').strip(), tokens[i+1].replace('.','').strip() ) )
            if unit is not None:
                units.append((i,unit.name,2))
                i+=1
                break
        unit = get_unit(tokens[i].replace('.','').strip())
        if unit is not None: 
            units.append((i,unit.name,1))
        i+=1
    return units

def findHeadings(tokens):
    # Don't do anything to change tokens.
    # headings: list of tuples of form
    # (heading index in tokens, heading_name, number of tokens comprising heading)
    headings = []
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 3:
            heading = get_heading('%s%s%s%s' % (tokens[i].replace('.','').replace('-','').strip(), tokens[i+1].replace('.','').replace('-','').strip(), tokens[i+2].replace('.','').replace('-','').strip(), tokens[i+3].replace('.','').replace('-','').strip()))
            if heading is not None: 
                headings.append((i,heading.name,4))
        if i < len(tokens) - 2:
            heading = get_heading('%s%s%s' % (tokens[i].replace('.','').replace('-','').strip(), tokens[i+1].replace('.','').replace('-','').strip(), tokens[i+2].replace('.','').replace('-','').strip()))
            if heading is not None: 
                headings.append((i,heading.name,3))
        if i < len(tokens) - 1:
            heading = get_heading('%s%s' % (tokens[i].replace('.','').replace('-','').strip(), tokens[i+1].replace('.','').replace('-','').strip()))
            if heading is not None: 
                headings.append((i,heading.name,2))
        heading = get_heading(tokens[i].replace('.','').replace('-','').strip())
        if heading is not None: 
            headings.append((i,heading.name,1))
        i+=1
    return headings
        
def findNumbers(tokens):
    # Don't do anything to change tokens.
    # numbers: list of tuples of form
    # (numnber's index in tokens, number value, count of tokens comprising number)
    numbers = []
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            number = get_number('%s%s' % (tokens[i].replace('.','').strip(), tokens[i+1].replace('.','').strip() ) )
            if number is not None:
                numbers.append((i,number,2))
                i+=1
                break
        number = get_number(tokens[i].replace('.','').strip())
        if number is not None: 
            numbers.append((i,number,1))
        i+=1
    return numbers

def retokenize(tokens):
    newtokens = []
    for token in tokens:
        test = separate_numbers_from_strings(token)
        for t in test:
            newtokens.append(t)
    return newtokens

def findNUH(loc):
    tokens = [x.strip() for x in loc.split()]
    # Preprocess the tokens to separate non-fraction numbers joined to strings
    retokens = retokenize(tokens)
    units = unitDictionary(retokens)
    if units is None:
        return None
#    headings = findHeadings(retokens)
    headings = headingDictionary(retokens)
    if headings is None:
        return None
    # Keep only unit, heading combinations that are sequential
#    uh = []
#    for heading in headings:
#        position = heading[0]
#        units1 = units[position-1]
#        if units[position-1] is not None:
#            #Find number preceding uh
#            uh.append(units)
#        try:
        
    for u in units:
        uend = units[u]['endtoken']
        if u > 0 and uend < len(retokens):
            for h in headings:
                if h == uend + 1:
                    offset = retokens[u-1]
                    if offset is not None:
                        start = u-1
                        end = headings[h]['endtoken']
                        numtokens = len(retokens)
                        i = 0
                        rest = ''
                        while i < start:
                            rest = (rest+" "+retokens[i]).strip()
                            i = i + 1
                        if rest != '':
                            return (offset, units[u]['unit'], headings[h]['heading'], rest)
                        i = end + 1
                        while i < numtokens:
                            rest = (rest+" "+retokens[i]).strip()
                            i = i + 1
                        if rest != '':
                            return (offset, units[u]['unit'], headings[h]['heading'], rest)
    return None

def parse_loc(loc, loctype):
   parts={}
   status=''
   if loctype.lower()=='f':
       if len(loc)==0:
           logging.info('No feature found in %s' % loc)
           status='No feature'

       # Try to construct a Feature from the remainder
       features=[]
       feature=loc.strip()
       features.append(feature)
       if len(status)==0:
           status='complete'
           interpreted_loc=feature
       parts = {
           'verbatim_loc': loc,
           'locality_type': loctype,
           'features': features,
           'feature_geocodes': None,
           'interpreted_loc': interpreted_loc,
           'status': status
           }                
       
   if loctype.lower()=='foh':
       # TODO: Start with what you know - find unit. Unit should be followed by heading
       # and preceded by distance.
       nuh = findNUH(loc)
       if nuh is None:
           # Most common form is number, unit, heading. Try this first. 
           # If this combo is not found, do further processing. Return None if an FOH can not be formed.
           return None
       status='nuh complete'

       # Try to construct a Feature from the remainder
       features=[]
       offsetval = nuh[0]
       offsetunit = nuh[1]
       heading = nuh[2]
       feature=nuh[3]
       feature=feature.strip()
       # Strip "stop" words off the beginning of the the putative feature
       fsplit = feature.split()
       if len(fsplit) > 1:
           stop_words = ['of','from','to']
           if fsplit[0].lower() in stop_words:
               feature=feature.lstrip(feature[0]).strip()
       features.append(feature)
       status='complete'
       interpreted_loc='%s %s %s %s' % (offsetval, offsetunit, heading, feature)
       parts = {
           'verbatim_loc': loc,
           'locality_type': loctype,
           'offset_value': offsetval,
           'offset_unit': offsetunit,
           'heading': heading,
           'features': features,
           'feature_geocodes': None,
           'interpreted_loc': interpreted_loc,
           'status': status
           }                
   return parts

def has_num(token):
    for c in token:
        if c.isdigit():
            return True
    return False

def get_fraction(token):
    frac = token.split('/')
    if len(frac)==2 and isdigit(frac[0]) and isdigit(frac[1]) and float(frac[1])!=0:
        return truncate(float(frac[0]/frac[1]),4)
    return None

def left(str, charcount):
    if charcount >= len(str):
        return str
    newstr = ''
    for i in range(charcount):
        newstr = '%s%s' % (newstr,str[i])
    return new_str

def right(str, charcount):
    if charcount >= len(str):
        return str
    newstr = ''
    strlen = len(str)
    for i in range(strlen - charcount, strlen):
        newstr = '%s%s' % (newstr,str[i])
    return newstr

def isDecimalIndicator(c):
    if c == '.':
        return True
    if c == ',':
        return True
    return False

def separate_numbers_from_strings(token):
    newtokens=[]
    # If it doesn't contain a number, return it as is.
    if not has_num(token):
        newtokens.append(token)
        return newtokens
    # If it is a number, return it as is.
    if is_number(token):
        newtokens.append(token)
        return newtokens
    # If it is a fraction, return it as is.
    if is_fraction(token):
        newtokens.append(token)
        return newtokens
    # If it isn't a number but starts with a number, return number and nonnumber tokens
    numstr = ''
    nonnumstr = '' 
    if token[0].isdigit() or isDecimalIndicator(token[0]):
        i = 0
        while i < len(token) and ( token[i].isdigit() or isDecimalIndicator(token[i]) ):
            numstr = '%s%s' % (numstr, token[i])
            i += 1
        nonnumstr = right(token, len(token) - i)
        newtokens.append(numstr)
        newtokens.append(nonnumstr)
        return newtokens
    # If it isn't a number but ends with a number, return nonnumber and number tokens
    i = 0
    while i < len(token) and not token[i].isdigit():
        nonnumstr = '%s%s' % (nonnumstr, token[i])
        i += 1
    numstr = right(tokens, len(token) - i)
    if is_num(numstr):
        newtokens.append(nonnumstr)
        newtokens.append(numstr)
        return newtokens
    # There is a number somewhere in the middle of the token
    newtokens.append(token)
    return newtokens

def get_number(s):
    try:
        float(s)
        return float(s)
    except ValueError:
        # s is not a number in the form of a float. Try other forms:
        # fractions such as 1/2
        # number words
        if has_num(s) is not None:
            pass
        return None

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False    

def is_fraction(token):
    frac = token.split('/')
    if len(frac) == 2 and is_number(frac[0]) and is_number(frac[1]):
        return True
    return False

class GeocodeResultParser(object):
    @classmethod
    def get_status(cls, geocode):
        if not geocode.has_key('status'):
            return None
        return geocode.get('status')

    @classmethod
    def get_feature_geoms(cls, featurename, geocode):
        if not geocode.has_key('status'):
            return None
        if geocode.get('status')!='OK':
            return None
        if not geocode.has_key('results'):
            return None
        results = geocode.get('results')
        geoms = []
        feature_sought = None
        for result in results:
            components = result.get('address_components')
            for component in components:
                if component.get('long_name').lower()==featurename.lower():
                    feature_sought = component
                    break
                if component.get('short_name').lower()==featurename.lower():
                    feature_sought = component
                    break
                if feature_sought is not None:
                    break
            if feature_sought is not None:
                geometry = result.get('geometry')
                geoms.append(geometry)
        return geoms

class GeometryParser(object):
    @classmethod
    def get_bb(cls, geometry):
        ''' Returns a BoundingBox object from a geocode response geometry dictionary.'''
        if geometry.has_key('bounds'):
            nw = Point(geometry['bounds']['southwest']['lng'], geometry['bounds']['northeast']['lat'])
            se = Point(geometry['bounds']['northeast']['lng'], geometry['bounds']['southwest']['lat'])
        elif geometry.has_key('location'):
            center = Point(geometry['location']['lng'], geometry['location']['lat'])
            if geometry.get('location_type') == 'ROOFTOP':
                return bb_from_pr(center,100) # default radius ROOFTOP type
            else: # location_type other than ROOFTOP and no bounds
                return bb_from_pr(center,1000)
        return BoundingBox(nw,se)
    
class PaperMap(object):
    def __init__(self, unit, datum):
        self._unit = unit
        self._datum = datum

    def getunit(self):
        return self._unit
    unit = property(getunit)

    def getdatum(self):
        return self._datum
    datum = property(getdatum)

    def getpoint(self, corner, ndist=None, sdist=None, edist=None, wdist=None):
        """Returns a lng, lat given a starting lng, lat and orthogonal offset distances.

        Arguments:
            corner - the lng, lat of the starting point.
            ndist - the distance north from corner along the same line of longitude to the 
                    latitude of the final point.
            sdist - the distance north from corner along the same line of longitude to the 
                    latitude of the final point.
            edist - the distance east from corner along the same line of latitude to the 
                    longitude of the final point.
            wdist - the distance west from corner along the same line of latitude to the 
                    longitude of the final point."""

        if (not ndist and not sdist) or (not edist and not wdist):
            return None
        if not self.unit:
            return None
        ns = 0.0
        ew = 0.0
        if ndist:
            ns = float(ndist)
            nsbearing = 0
        elif sdist:
            ns = float(sdist)
            nsbearing = 180
        if edist:
            ew = float(edist)
            ewbearing = 90
        elif wdist:
            ew = -float(wdist)
            ewbearing = 270
        # convert distances to meters
        ns = ns * get_unit(self.unit).tometers
        ew = ew * get_unit(self.unit).tometers
        # get coordinates of ns offset and ew offset
        nspoint = corner.get_point_from_distance_at_bearing(ns, nsbearing)
        ewpoint = corner.get_point_from_distance_at_bearing(ew, ewbearing)
        return Point(ewpoint.lng, nspoint.lat)

class Georeference(object):
    def __init__(self, point, error):
        self.point = point
        self.error = error
        
    def get_error(self):
        # error formatted to the nearest higher meter.
        ferror = int(math.ceil(self.error))
        return ferror
    
    def get_point(self):
        # latitude, longitude formatted to standardized precision
        flat = truncate(self.point.lat, DEGREE_DIGITS)
        flng = truncate(self.point.lng,DEGREE_DIGITS)
        return Point(flng, flat)
    
    def __str__(self):
        return str(self.__dict__)

def get_unit(unitstr):
    """Returns a DistanceUnit from a string."""
    u = unitstr.replace('.', '').strip().lower()
    for unit in DistanceUnits.all():
        for form in unit.forms:
            if u == form:
                return unit
    return None

def get_heading(headingstr):
    """Returns a Heading from a string."""
    h = headingstr.replace('-', '').replace(',', '').strip().lower()
    for heading in Headings.all():
        for form in heading.forms:
            if h == form:
                return heading
    return None

#def georef_feature(geocode):
#    """Returns a Georeference from the Geomancer API.
#        Arguments:
#            geocode - a Maps API JSON response for a feature
#    """
#    if not geocode:
#        return None
#    status = geocode.get('status')
#    if status != 'OK':
#        # Geocode failed, no results, no georeference possible.
#        return None
#    if geocode.get('results')[0].has_key('geometry') == False:
#        # First result has no geometry, no georeference possible.
#        return None
#    g = geocode.get('results')[0].get('geometry')
#    point = GeocodeResultParser.get_point(g)
#    error = GeocodeResultParser.calc_radius(g)
#    return Georeference(point, error)

#def georeference(locality):
#    """Returns a Georeference given a Locality.
#        Arguments:
#            locality - the Locality to georeference
#    """
#    if not locality:
#        return None
#    if not locality.loctype:
#        # Georeference as feature-only using the geocode.
#        return georef_feature(locality.geocode)
#    if locality.loctype == 'foh':
#        unitstr = locality.parts.get('offset_unit')
#        headingstr = locality.parts.get('heading')
#        offset = locality.parts.get('offset_value')
#        featuregeocode = locality.parts.get('feature').get('geocode')
#        # Get the feature, then do the `.
#        feature = georef_feature(featuregeocode)
#        error = foh_error(feature.point, feature.error, offset, unitstr, headingstr)
#        # get a bearing from the heading
#        bearing = float(get_heading(headingstr).bearing)
#        fromunit = get_unit(unitstr)
#        offsetinmeters = float(offset) * float(fromunit.tometers)        
#        newpoint = get_point_from_distance_at_bearing(feature.point, offsetinmeters, bearing)
#        return Georeference(newpoint, error)

def foh_error_bb(bb, offset, offsetunit, heading):
    center = bb.center()
    extent = bb.calc_radius()
    error = foh_error(center,extent,offset,offsetunit,heading)
    bearing = float(get_heading(heading).bearing)
    fromunit = get_unit(offsetunit)
    offsetinmeters = float(offset) * float(fromunit.tometers)    
    newpoint = center.get_point_from_distance_at_bearing(offsetinmeters, bearing)
    newbb = bb_from_pr(newpoint,error)
    return newbb

def foh_error(point, extent, offsetstr, offsetunits, headingstr):
    """Returns the radius in meters from a Point containing all of the uncertainties
    for a Locality of type Feature Offset Heading.
    
    Arguments:
        point - the center of the feature in the Locality
        extent - the radius from the center of the Feature to the furthest corner of the bounding
                 box containing the feature, in meters
        offset - the distance from the center of the feature, as a string
        offsetunits - the units of the offset
        headingstr - the direction from the feature to the location
        
    Note: all sources for error are shown, though some do not apply under the assumption of using the 
    Google Geocoding API for get the feature information."""
    # error in meters
    error = 0
    # No datum error - always WGS84
#      error += datumError(datum, point)
    # No source error from Maps Geocoding API
#      error += sourceError(source)
    error += extent
    # offset must be a string in this call
    distprecision = getDistancePrecision(offsetstr)
    fromunit = get_unit(offsetunits)
    # distance precision in meters
    dpm = distprecision * float(fromunit.tometers)
    error += dpm
    # Convert offset to meters
    offsetinmeters = float(offsetstr) * float(fromunit.tometers)
    # Get error angle from heading
    error = getDirectionError(error, offsetinmeters, headingstr)
    # No coordinate error from Maps Geocoding API - more than six digits retained
#    error += coordinatesPrecisionError(coordinates)
    return error

def getDirectionError(starterror, offset, headingstr):
    """Returns the error due to direction given a starting error, an offset, and a heading from a Point.

    Arguments:
        starterror - accumulated initial error from extent, etc., in meters
        offset - the linear distance from the starting coordinate, in meters
        headingstr - the direction from the feature to the location""" 
    
    headingerror = float(get_heading(headingstr).error)
    x = offset * math.cos(math.radians(headingerror))
    y = offset * math.sin(math.radians(headingerror))
    xp = offset + starterror
    neterror = math.sqrt(math.pow(xp - x, 2) + math.pow(y, 2))
    return neterror

def getDistancePrecision(distance):
    """Returns the precision of the string representation of the distance as a value in the same units.
    
    Arguments:
        distance - the distance for which the precision is to be determined, as a string

    Reference: Wieczorek, et al. 2004, MaNIS/HerpNet/ORNIS Georeferencing Guidelines, 
    http://manisnet.org/GeorefGuide.html
    
    Note: Calculations modified for fractions to be one-half of that described in the paper, 
    which we now believe to be unreasonably conservative."""
    if type(distance) != str and type(distance) != unicode:
        return None
    try:
        float(distance)
    except:
        return None
    if float(distance) < 0:
        return None
    if float(distance) < 0.001:
        return 0.0
    # distance is a non-negative number expressed as a string
    # Strip it of white space and put it in English decimal format
    d = distance.strip().replace(',','.')
    offsetuncertainty = 0.0
    offset = float(distance)
    # significant digits to the right of the decimal
    sigdigits = 0 
    offsetuncertainty = 1
    hasdecimal = len(distance.split('.')) - 1
    if hasdecimal > 0:    
        sigdigits = len(distance.split('.')[1])
    if sigdigits > 0:
        #If the last digit is a zero, the original was specified to that level of precision.
        if distance[len(distance)-1] == '0':
            offsetuncertainty = 1.0 * math.pow(10.0, -1.0 * sigdigits) 
            # Example: offsetstring = "10.0" offsetuncertainty = 0.1
        else:
            # Significant digits, but last one not '0'
            # Otherwise get the fractional part of the interpreted offset. 
            # We'll use this to determine uncertainty.
            fracpart, intpart = math.modf(float(offset))
            # Test to see if the fracpart can be turned in to any of the target fractions.
            # fracpart/testfraction = integer within a predefined level of tolerance.
            denominators = [2.0, 3.0, 4.0, 8.0, 10.0, 100.0, 1000.0]
            for d in denominators:
              numerator, extra = math.modf(fracpart * d)
              '''If the numerator is within tolerance of being an integer, then the
                denominator represents the distance precision in the original
                units.'''
              if numerator < 0.001 or math.fabs(numerator - 1) < 0.001:
                  # This denominator appears to represent a viable fraction.
                  offsetuncertainty = 1.0 / d
                  break
    else:
        powerfraction, powerint = math.modf(math.log10(offset))
        # If the offset is a positive integer power of ten.
        while offset % math.pow(10, powerint) > 0:
            powerint -= 1
        offsetuncertainty = math.pow(10.0, powerint)
    offsetuncertainty = offsetuncertainty * 0.5
    return offsetuncertainty
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
