import math
import logging
from geomancer.constants import DistanceUnits, Headings
from geomancer.model import *
from geomancer.point import *
from geomancer.bb import *
from google.appengine.ext import ndb

def findHeadings(tokens):
    # Don't do anything to change tokens.
    # headings: list of tuples of form
    # (heading index in tokens, heading_name, number of tokens comprising heading)
    headings = []
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 3:
            heading = get_heading('%s%s%s%s' % 
                        (tokens[i].replace('.', '').replace('-', '').strip(),
                         tokens[i + 1].replace('.', '').replace('-', '').strip(),
                         tokens[i + 2].replace('.', '').replace('-', '').strip(),
                         tokens[i + 3].replace('.', '').replace('-', '').strip()))
            if heading is not None: 
                headings.append((i, heading.name, 4))
        if i < len(tokens) - 2:
            heading = get_heading('%s%s%s' % 
                        (tokens[i].replace('.', '').replace('-', '').strip(),
                         tokens[i + 1].replace('.', '').replace('-', '').strip(),
                         tokens[i + 2].replace('.', '').replace('-', '').strip()))
            if heading is not None: 
                headings.append((i, heading.name, 3))
        if i < len(tokens) - 1:
            heading = get_heading('%s%s' % 
                        (tokens[i].replace('.', '').replace('-', '').strip(),
                         tokens[i + 1].replace('.', '').replace('-', '').strip()))
            if heading is not None: 
                headings.append((i, heading.name, 2))
        heading = get_heading(tokens[i].replace('.', '').replace('-', '').strip())
        if heading is not None: 
            headings.append((i, heading.name, 1))
        i += 1
    return headings
        
def findNUH(loc):
    tokens = [x.strip() for x in loc.split()]
    # Preprocess the tokens to separate non-fraction numbers joined to strings
    retokens = retokenize(tokens)
    units = unitDictionary(retokens)
    if units is None:
        return None
    headings = headingDictionary(retokens)
    if headings is None:
        return None

    for u in units:
        uend = units[u]['endtoken']
        if u > 0 and uend < len(retokens):
            for h in headings:
                if h == uend + 1:
                    offset = retokens[u - 1]
                    if offset is not None:
                        start = u - 1
                        end = headings[h]['endtoken']
                        numtokens = len(retokens)
                        i = 0
                        rest = ''
                        while i < start:
                            rest = (rest + " " + retokens[i]).strip()
                            i = i + 1
                        if rest != '':
                            return (offset, units[u]['unit'],
                                    headings[h]['heading'], rest)
                        i = end + 1
                        while i < numtokens:
                            rest = (rest + " " + retokens[i]).strip()
                            i = i + 1
                        if rest != '':
                            return (offset, units[u]['unit'],
                                    headings[h]['heading'], rest)
    return None

def findNumbers(tokens):
    # Don't do anything to change tokens.
    # numbers: list of tuples of form
    # (numnber's index in tokens, number value, count of tokens comprising number)
    numbers = []
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            number = get_number('%s%s' % 
                        (tokens[i].replace('.', '').strip(),
                         tokens[i + 1].replace('.', '').strip()))
            if number is not None:
                numbers.append((i, number, 2))
                i += 1
                break
        number = get_number(tokens[i].replace('.', '').strip())
        if number is not None: 
            numbers.append((i, number, 1))
        i += 1
    return numbers

def findUnits(tokens):
    # Don't do anything to change tokens.
    # units: list of tuples of form
    # (unit index in tokens, unit_name, number of tokens comprising unit)
    units = []
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            unit = get_unit('%s%s' % 
                            (tokens[i].replace('.', '').strip(),
                             tokens[i + 1].replace('.', '').strip()))
            if unit is not None:
                units.append((i, unit.name, 2))
                i += 1
                break
        unit = get_unit(tokens[i].replace('.', '').strip())
        if unit is not None: 
            units.append((i, unit.name, 1))
        i += 1
    return units

def foh_error(point, extent, offsetstr, offsetunits, headingstr):
    """ Returns the radius in meters from a Point containing all of the 
        uncertainties for a Locality of type Feature Offset Heading.
    
    Arguments:
        point - the center of the feature in the Locality
        extent - the radius from the center of the Feature to the furthest 
                 corner of the bounding box containing the feature, in meters
        offset - the distance from the center of the feature, as a string
        offsetunits - the units of the offset
        headingstr - the direction from the feature to the location
        
    Note: all sources for error are shown, though some do not apply under 
    the assumption of using the Google Geocoding API for get the feature 
    information."""
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
    # No coordinate error from Maps Geocoding API - more than six digits 
    # retained
#    error += coordinatesPrecisionError(coordinates)
    return error

def foh_error_point(center, extentstr, offset, offsetunit, heading):
    if center is None:
        return None
    if extentstr is None:
        return None
    extent = get_number(extentstr)
    error = foh_error(center, extent, offset, offsetunit, heading)
    bearing = float(get_heading(heading).bearing)
    fromunit = get_unit(offsetunit)
    offsetinmeters = float(offset) * float(fromunit.tometers)    
    newpoint = center.get_point_on_rhumb_line(offsetinmeters, bearing)
    bb = bb_from_pr(newpoint,error)
    georef = bb_to_georef(bb)
    return georef

def getDirectionError(starterror, offset, headingstr):
    """ Returns the error due to direction given a starting error, an offset, 
        and a heading from a Point.

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
    """ Returns the precision of the string representation of the distance as a 
        value in the same units.
    
    Arguments:
        distance - the distance for which the precision is to be determined, as 
                   a string

    Reference: Wieczorek, et al. 2004, MaNIS/HerpNet/ORNIS Georeferencing 
    Guidelines, http://manisnet.org/GeorefGuide.html
    
    Note: Calculations modified for fractions to be one-half of that described 
    in the paper, which we now believe to be unreasonably conservative."""
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
    d = distance.strip().replace(',', '.')
    offsetuncertainty = 0.0
    offset = float(distance)
    # significant digits to the right of the decimal
    sigdigits = 0 
    offsetuncertainty = 1
    hasdecimal = len(distance.split('.')) - 1
    if hasdecimal > 0:    
        sigdigits = len(distance.split('.')[1])
    if sigdigits > 0:
        #If the last digit is a zero, the original was specified to that level 
        # of precision.
        if distance[len(distance) - 1] == '0':
            offsetuncertainty = 1.0 * math.pow(10.0, -1.0 * sigdigits) 
            # Example: offsetstring = "10.0" offsetuncertainty = 0.1
        else:
            # Significant digits, but last one not '0'
            # Otherwise get the fractional part of the interpreted offset. 
            # We'll use this to determine uncertainty.
            fracpart, intpart = math.modf(float(offset))
            # Test to see if the fracpart can be turned in to any of the target 
            # fractions.
            # fracpart/testfraction = integer within a predefined level of 
            # tolerance.
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
    
def get_fraction(token):
    frac = token.split('/')
    if len(frac) == 2 and frac[0].isdigit() and frac[1].isdigit() and \
        float(frac[1]) != 0:
        return truncate(float(frac[0]) / float(frac[1]), 4)
    return None

def get_georefs_from_parts(parts): 
    if parts is None:
        return None
    feature_geocodes = parts.get('feature_geocodes')
    if feature_geocodes is None:
        return None
    loc_type = parts.get('locality_type')
    if loc_type is None:
        return None
    
    georefs=[]
    if loc_type == 'f':
        for geocode in feature_geocodes.values():
#            logging.info('GEOCODE %s' % geocode)
            feature_georefs = get_maps_response_georefs(geocode)
            for g in feature_georefs:
                georefs.append(g)
    elif loc_type == 'foh':
        for geocode in feature_geocodes.values():
#            logging.info('GEOCODE %s' % geocode)
            feature_georefs = get_maps_response_georefs(geocode)
            for g in feature_georefs:
                flat = g['lat']
                flng = g['lng']
                func = g['uncertainty']
                offset = parts['offset_value']
                offsetunit = parts['offset_unit']
                heading = parts['heading'] 
                georef = foh_error_point(Point(flng,flat), func, offset, offsetunit, 
                    heading)
                if georef is not None:
                    georefs.append(georef)
    else:
        return None
    return georefs

def get_heading(headingstr):
    """Returns a Heading from a string."""
    h = headingstr.replace('-', '').replace(',', '').strip().lower()
    for heading in Headings.all():
        for form in heading.forms:
            if h == form:
                return heading
    return None

def get_maps_response_georefs(response):
    georefs = []
    results = response.get('results')
    if results is None:
        return None
    for result in results:
        geom = result.get('geometry')
        if geom is not None:
            bb = geom_to_bb(geom)
            georef = bb_to_georef(bb)
            if georef is not None:
                georefs.append(georef)
    return georefs

def bb_to_georef(bb):
    if bb is None:
        return None
    if not bb.isvalid:
        return None
    ne = {}
    sw = {}
    ne['lat'] = bb.nw.lat
    ne['lng'] = bb.se.lng
    sw['lat'] = bb.se.lat
    sw['lng'] = bb.nw.lng
    bounds = {}
    bounds['northeast'] = ne
    bounds['southwest'] = sw
    center = bb.center()
    georef = {
              'lat': center.lat,
              'lng': center.lng,
              'uncertainty': bb.calc_radius(),
              'bounds': bounds
              }
    return georef

def clauses_from_locality(location):
    """Return list of Locality objects by splitting location on ',' and ';'."""
    clause_names = [name.strip() for name in set(reduce(
                lambda x, y: x + y,
                [x.split(';') for x in location.split(',')]))]
    normalized_clause_names = []
    for clause_name in clause_names:
        tokens = [x.strip() for x in clause_name.split()]
        new_clause_name = rebuild_from_tokens(retokenize(tokens)).lower().strip()
        normalized_clause_names.append(new_clause_name) 
    return normalized_clause_names

def geom_to_bb(geometry):
    ''' Returns a BoundingBox object from a geocode response geometry 
        dictionary.'''
    if geometry.has_key('bounds'):
        nw = Point(geometry['bounds']['southwest']['lng'],
                   geometry['bounds']['northeast']['lat'])
        se = Point(geometry['bounds']['northeast']['lng'],
                   geometry['bounds']['southwest']['lat'])
        return BoundingBox(nw, se)
    if geometry.has_key('location'):
        center = Point(geometry['location']['lng'],
                       geometry['location']['lat'])
        geom_type = geometry.get('location_type')
    if geom_type == 'ROOFTOP':
        return bb_from_pr(center, 30)
    if geom_type == 'RANGE_INTERPOLATED':
        return bb_from_pr(center, 100)
    return bb_from_pr(center, 1000)

def get_number(s):
    try:
        float(s)
        return float(s)
    except ValueError:
        # s is not a number in the form of a float. Try other forms:
        # fractions such as 1/2
        # number words
        return get_fraction(s)

def get_unit(unitstr):
    """Returns a DistanceUnit from a string."""
    u = unitstr.replace('.', '').strip().lower()
    for unit in DistanceUnits.all():
        for form in unit.forms:
            if u == form:
                return unit
    return None

def has_num(token):
    for c in token:
        if c.isdigit():
            return True
    return False

def headingDictionary(tokens):
    headings = {}
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            heading = get_heading('%s%s' % 
                                  (tokens[i].replace('.', '').strip(),
                                   tokens[i + 1].replace('.', '').strip()))
            if heading is not None:
                headings[i] = {'heading':heading.name, 'endtoken':i + 1}
                i += 1
                break
        heading = get_heading(tokens[i].replace('.', '').strip())
        if heading is not None: 
            headings[i] = {'heading':heading.name, 'endtoken':i}
        i += 1
    return headings
    
def isDecimalIndicator(c):
    if c == '.':
        return True
    if c == ',':
        return True
    return False
    
def is_fraction(token):
    frac = token.split('/')
    if len(frac) == 2 and is_number(frac[0]) and is_number(frac[1]):
        return True
    return False

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False    

def left(str, charcount):
    if charcount >= len(str):
        return str
    newstr = ''
    for i in range(charcount):
        newstr = '%s%s' % (newstr, str[i])
    return new_str

def loc_georefs(clauses):
    """Get georefs for each Clause in supplied list."""
    georef_lists = [x.georefs for x in clauses]
    if len(georef_lists) == 0:
        return None
    logging.info('GEOREF_LISTS %s' % georef_lists)
    results = georef_lists.pop()
    while len(georef_lists) > 0:
        new_results = []
        next_georefs = georef_lists.pop()
        for result in results:
            logging.info('RESULT %s' % result)
            w, s, e, n = result.get().bbox
            for next_georef in next_georefs:
                logging.info('NEXT %s' % next_georef)
                n_w, n_s, n_e, n_n = next_georef.get().bbox
                resultbb = BoundingBox(Point(w,n), Point(e,s))
                nextbb = BoundingBox(Point(n_w, n_n),
                                       Point(n_e, n_s))
                new_result = resultbb.intersection(nextbb)
                if new_result is not None:
                    new_results.append(bb_to_georef(new_result))
        results = new_results
        logging.info("PLEEEEEEEEEEASE %s" % results)
        results = map(Georef.from_dict, results)
        ndb.put_multi(results)
        results = [x.key for x in results]
    logging.info("WHHHHHAAA %s" % results)
    return results

def parse_loc(loc, loctype):
   parts = {}
   status = ''
   if loctype.lower() == 'f':
       if len(loc) == 0:
           logging.info('No feature found in %s' % loc)
           status = 'No feature'

       # Try to construct a Feature from the remainder
       features = []
       feature = loc.strip()
       features.append(feature)
       if len(status) == 0:
           status = 'complete'
           interpreted_loc = feature
       parts = {
           'verbatim_loc': loc,
           'locality_type': loctype,
           'features': features,
           'feature_geocodes': None,
           'interpreted_loc': interpreted_loc,
           'status': status
           }                
       
   if loctype.lower() == 'foh':
       # TODO: Start with what you know - find unit. Unit should be followed 
       # by heading and preceded by distance.
       nuh = findNUH(loc)
       if nuh is None:
           # Most common form is number, unit, heading. Try this first. 
           # If this combo is not found, do further processing. Return None 
           # if an FOH can not be formed.
           return None
       status = 'nuh complete'

       # Try to construct a Feature from the remainder
       features = []
       offsetval = nuh[0]
       offsetunit = nuh[1]
       heading = nuh[2]
       feature = nuh[3]
       feature = feature.strip()
       # Strip "stop" words off the beginning of the the putative feature
       fsplit = feature.split()
       if len(fsplit) > 1:
           stop_words = ['of', 'from', 'to']
           if fsplit[0].lower() in stop_words:
               feature = feature.lstrip(fsplit[0]).strip()
       features.append(feature)
       status = 'complete'
       interpreted_loc = '%s %s %s %s' % (offsetval, offsetunit, heading, feature)
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

def rebuild_from_tokens(tokens):
    return ' '.join(tokens)

def retokenize(tokens):
    newtokens = []
    hasfraction = -1
    hasnum = -1
    i = 0
    for token in tokens:
        test = separate_numbers_from_strings(token)
        if len(newtokens) > 0 and is_number(newtokens[len(newtokens) - 1]) \
            and is_number(test[0]) and float(test[0]) < 1:
            hasfraction = i
        for t in test:
            newtokens.append(t)
            i = i + 1
    finaltokens = []
    i = 0
    for token in newtokens:
        if i == hasfraction - 1:
            combo = float(newtokens[hasfraction - 1]) + float(newtokens[hasfraction])
            finaltokens.append(str(combo))
        elif i == hasfraction:
            pass
        elif is_number(token):
            finaltokens.append(token)
        else:
            finaltokens.append(token.strip('.'))
        i = i + 1
    return finaltokens
    
def right(str, charcount):
    if charcount >= len(str):
        return str
    newstr = ''
    strlen = len(str)
    for i in range(strlen - charcount, strlen):
        newstr = '%s%s' % (newstr, str[i])
    return newstr

def separate_numbers_from_strings(token):
    newtokens = []
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
        frac = get_fraction(token)
        newtokens.append(frac)
        return newtokens
    # If it isn't a number but starts with a number, return number and 
    # non-number tokens
    numstr = ''
    nonnumstr = '' 
    if token[0].isdigit() or isDecimalIndicator(token[0]):
        i = 0
        while i < len(token) and \
            (token[i].isdigit() or \
             token[i]=='/' or \
            isDecimalIndicator(token[i])):
            numstr = '%s%s' % (numstr, token[i])
            i += 1
        nonnumstr = right(token, len(token) - i)
        f = get_fraction(numstr)
        if f is not None:
            newtokens.append(f)
        else:
            newtokens.append(numstr)
        newtokens.append(nonnumstr)
        return newtokens
    # If it isn't a number but ends with a number, return non-number and 
    # number tokens
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

def unitDictionary(tokens):
    units = {}
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            unit = get_unit('%s%s' % (tokens[i].replace('.', '').strip(),
                                      tokens[i + 1].replace('.', '').strip()))
            if unit is not None:
                units[i] = {'unit':unit.name, 'endtoken':i + 1}
                i += 1
                break
        unit = get_unit(tokens[i].replace('.', '').strip())
        if unit is not None: 
            units[i] = {'unit':unit.name, 'endtoken':i}
        i += 1
    return units
    
