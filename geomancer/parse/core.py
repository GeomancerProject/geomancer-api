import logging
from geomancer.constants import DistanceUnits, Headings

DEGREE_DIGITS = 7

FORMAT = """.%sf"""

def truncate(x, digits):
    """Returns x including precision to the right of the decimal equal to digits."""
    format_x = FORMAT % digits
    return format(x,format_x)

def unitDictionary(tokens):
    units = {}
    i = 0
    while i < len(tokens):
        if i < len(tokens) - 1:
            # TODO? These are unused:
            # ti = tokens[i] 
            # ti1 = tokens[i+1]
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
            # TODO? These are unused:            
            # ti = tokens[i]
            # ti1 = tokens[i+1]
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
    if len(frac)==2 and frac[0].isdigit() and frac[1].isdigit() and float(frac[1])!=0:
        return truncate(float(frac[0]/frac[1]),4)
    return None

def left(str, charcount):
    if charcount >= len(str):
        return str
    newstr = ''
    for i in range(charcount):
        newstr = '%s%s' % (newstr,str[i])
    return newstr

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
    
    # TODO: tokens not defines, is_num not defined.
    #numstr = right(tokens, len(token) - i)
    #if is_num(numstr):
    
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
