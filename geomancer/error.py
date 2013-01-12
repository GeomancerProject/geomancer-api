from geomancer.parse.core import *
from geomancer.point import *

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
		georefs = get_maps_response_georefs(feature_geocodes)
	elif loc_type == 'foh':
		for geocode in feature_geocodes.values():
			feature_georefs = get_maps_response_georefs(geocode)
			for g in feature_georefs:
				flat = get_number(g['lat'])
				flng = get_number(g['lng'])
				func = get_number(g['uncertainty'])
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


