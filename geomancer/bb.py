#!/usr/bin/env python

# Copyright 2011 University of California at Berkeley
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

__author__ = "Aaron Steele and John Wieczorek"

import logging
from point import *
from optparse import OptionParser
import math

class BoundingBox(object):
    """A degree-based geographic bounding box independent of a coordinate reference system."""

    def __init__(self, nw, se):
        self._nw = nw
        self._se = se
    
    def get_nw(self):
        return self._nw
    nw = property(get_nw)
    
    def get_se(self):
        return self._se
    se = property(get_se)
    
    def get_n(self):
        return self._nw.get_lat()
    
    def get_w(self):
        return self._nw.get_lng()
    
    def get_s(self):
        return self._se.get_lat()
    
    def get_e(self):
        return self._se.get_lng()

    def isvalid(self):
        if nw.isvalid:
            if se.isvalid:
                return True
        return False

    def to_kml(self):
        polygon = '<Polygon><outerBoundaryIs><coordinates>%s</coordinates></outerBoundaryIs></Polygon>'
        n = self.get_n()
        s = self.get_s()
        e = self.get_e()
        w = self.get_w()
        coords = '%s,%s %s,%s %s,%s %s,%s %s,%s' % (w,n,w,s,e,s,e,n,w,n)
        return polygon % coords

    @classmethod
    def create(cls, xmin, ymax, xmax, ymin):
        return cls(Point(xmin, ymax), Point(xmax, ymin))
    
    def __repr__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        if not isinstance(other, BoundingBox):
            return NotImplemented
        if self.nw != other.nw:
            return NotImplemented
        if self.se != other.se:
            return NotImplemented
        return True

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return hash('%s,%s %s,%s' % (self.get_w(), self.get_n(), self.get_e(), self.get_s()))

    def __cmp__(self, other):
        if self.__eq__(other):
            return 0
        if self.nw.__gt__(other.nw):
            return 1
        return -1

    @classmethod
    def get_intersecting(cls, bb_list):
        pass # TODO

    @classmethod
    def intersect_all(cls, bb_list):
        n = len(bb_list)
        if n == 1:
            return bb_list[0]
        if n == 0:
            return None
        result = bb_list.pop(0)
        for bb in bb_list:
            result = bb.intersection(result)
            if result is None:
                return None
        return result
    
    def intersection(self,bb):
        """Returns a BoundingBox created from an intersection or None."""
        my_n=self.nw.get_lat()
        my_s=self.se.get_lat()
        my_w=self.nw.get_lng()
        my_e=self.se.get_lng()
        bb_n=bb.nw.get_lat()
        bb_s=bb.se.get_lat()
        bb_w=bb.nw.get_lng()
        bb_e=bb.se.get_lng()
        n,s,w,e = None, None, None, None
        if my_s <= bb_n and bb_n <= my_n:
            n=bb_n
        elif bb_s <= my_n and my_n <= bb_n:
            n=my_n
        if n is None:
            return None

        if my_s <= bb_s and bb_s <= my_n:
            s=bb_s
        elif bb_s <= my_s and my_s <= bb_n:
            s=my_s
        if s is None:
            return None

        if is_lng_between(bb_w, my_w,my_e):
            w=bb_w
        elif is_lng_between(my_w, bb_w,bb_e):
            w=my_w
        if w is None:
            return None

        if is_lng_between(bb_e, my_w,my_e):
            e=bb_e
        elif is_lng_between(my_e, bb_w,bb_e):
            e=my_e
        if e is None:
            return None
        return BoundingBox(Point(w,n),Point(e,s))
    
    def center(self):
        return great_circle_midpoint(self.nw,self.se)
    
    def calc_radius(self):
        """Returns a radius in meters from the center to the farthest corner of the bounding box."""
        return self.se.haversine_distance(self.nw)/2.0
  
# Inject here for MoL
# http://code.google.com/apis/maps/documentation/javascript/maptypes.html#CustomMapTypes
    def get_tile_origin(self, tile_x, tile_y, zoom):
        '''Return the lat, lng of the northwest corner of the tile.'''
        tile_width = 360.0/pow(2,zoom) # degrees
        tile_height = tile_width/2        # degrees
        n = 90 - tile_y * tile_height
        w = -180 + tile_x * tile_width
        return (n,w)
        
    def get_bb(self, tile_x, tile_y, zoom):
        """Return bounding coordinates (n, e, s, w) of the tile."""
        tile_width = 360.0/pow(2,zoom) # degrees
        tile_height = tile_width/2   # degrees
        n = 90 - tile_y * tile_height
        s = n - tile_height
        w = -180 + tile_x * tile_width
        e = w + tile_width
        return (n, e, s, w)
        
    def bboxfromxyz(self, x,y,z):             
        pixels = 256
        
        res = (2 * math.pi * 6378137 / pixels) / (2**int(z))
        sh = 2 * math.pi * 6378137 / 2.0
    
        gy = (2**float(z) - 1) - int(y)
        minx, miny = ((float(x)*pixels) * res - sh),      (((float(gy))*pixels) * res - sh)
        maxx, maxy = (((float(x)+1)*pixels) * res - sh),  (((float(gy)+1)*pixels) * res - sh)
        
        minx, maxx = (minx / sh) * 180.0, (maxx / sh) * 180.0
        miny, maxy = (miny / sh) * 180.0, (maxy / sh) * 180.0
        miny = 180 / math.pi * (2 * math.atan( math.exp( miny * math.pi / 180.0)) - math.pi / 2.0)
        maxy = 180 / math.pi * (2 * math.atan( math.exp( maxy * math.pi / 180.0)) - math.pi / 2.0)
        return minx,miny,maxx,maxy
 
    def world_coord_from_point(self, zoom, lat, lng):
        '''Return the number of pixels in x, and y given 0,0 at lat=90, lng=-180'''
        pixel_x = int(256*(lng+180)/360.0 * pow(2,zoom))
        pixel_y = int(256*(90-lat)/180.0 * pow(2,zoom))
        return (pixel_x, pixel_y)
    
    def tile_from_point(self, zoom, lat, lng):
        ''' Return a tuple containing the x, y tile index.'''
        pixel_x, pixel_y = self.world_coord_from_point(zoom, lat, lng)
        tile_x = int(pixel_x / 256.0)
        tile_y = int(pixel_y / 256.0)
        return (tile_x, tile_y)
          
    def get_tile_coordinate(self, zoom, lat, lng):
        """Returns the offset in pixels from origin of the tile in the nw corner."""
        tile_x, tile_y = self.tile_from_point(zoom, lat, lng)
        n, w = self.get_tile_origin(tile_x, tile_y, zoom)
        world_x, world_y = self.world_coord_from_point(zoom, lat, lng)
        left, top = self.world_coord_from_point(zoom,n,w)
        x_offset = world_x - left
        y_offset = world_y - top
        return (x_offset, y_offset)

def is_lng_between(lng, west_lng, east_lng):
    '''
    Returns true if the given lng is between the longitudes west_lng and east_lng
    proceeding east from west_lng to east_lng.
    '''
    west_to_east = lng_distance(west_lng, east_lng)
    lng_to_east = lng_distance(lng, east_lng)
    if west_to_east >= lng_to_east:
        return True
    return False

def lng_distance(west_lng, east_lng):
    '''Returns the number of degrees from west_lng going eastward to east_lng.'''
    w = lng180(west_lng)
    e = lng180(east_lng)
    if w==e:
        '''
        Convention: If west and east are the same, the whole circumference is meant 
        rather than no difference.
        '''
        return 360
    if e <= 0:
        if w <= 0:
            if w > e:
                '''w and e both in western hemisphere with w east of e.'''
                return 360 + e - w
            '''w and e in western hemisphere with w west of e.'''
            return e - w
        '''w in eastern hemisphere and e in western hemisphere.'''
        return 360 + e - w
    if w <= 0:
        '''w in western hemisphere and e in eastern hemisphere.'''
        return e - w
    if w > e:
        '''w and e both in eastern hemisphere with w east of e.''' 
        return 360 + e - w
    '''w and e both in eastern hemisphere with w west or e.'''
    return e - w

def bb_from_pr(center,radius):
    n = center.get_point_on_rhumb_line(radius,0)
    e = center.get_point_on_rhumb_line(radius,90)
    s = center.get_point_on_rhumb_line(radius,180)
    w = center.get_point_on_rhumb_line(radius,270)
    nw = Point(w.lng,n.lat)
    se = Point(e.lng,s.lat)
    return BoundingBox(nw,se)

def great_circle_midpoint(p0,p1):
    """
    Return the midpoint of two ends of the great circle route between two lat, lngs. Orientation matters - p0 should be west of p1.
    """
    lat1 = math.radians(p0.lat)
    lat2 = math.radians(p1.lat)
    lng1 = math.radians(p0.lng)
    lng2 = math.radians(p1.lng)
    dlng = lng2 - lng1
    bx = math.cos(lat2) * math.cos(dlng)
    by = math.cos(lat2) * math.sin(dlng)
    lat3 = math.atan2(math.sin(lat1) + math.sin(lat2), math.sqrt( (math.cos(lat1) + bx) * (math.cos(lat1)+bx) + by*by) ) 
    lng3 = lng1 + math.atan2(by, math.cos(lat1) + bx)
    return Point(math.degrees(lng3),math.degrees(lat3))

def _getoptions():
    """Parses command line options and returns them."""
    parser = OptionParser()
    parser.add_option("-c", "--command", dest="command",
                      help="Command to run",
                      default=None)
    parser.add_option("-1", "--bb1", dest="bb1",
                      help="NW corner of one bounding box",
                      default=None)
    parser.add_option("-2", "--bb2", dest="bb2",
                      help="NW corner of second bounding box",
                      default=None)
    return parser.parse_args()[0]

def main():
    logging.basicConfig(level=logging.DEBUG)
    options = _getoptions()
    command = options.command.lower()
    
    logging.info('COMMAND %s' % command)

    if command=='help':
        print 'syntax: -c intersection -1 w_lng,n_lat|e_lng,s_lat -2 w_lng,n_lat|e_lng,s_lat'
        return

    if command=='intersect':
        if options.bb1 is None:
            print 'bb1 argument missing'
            return
        if options.bb2 is None:
            print 'bb2 argument missing'
            return
        nw, se = options.bb1.split('|')
        w, n = nw.split(',')
        e, s = se.split(',')
        pnw=Point(float(w),float(n))
        pse=Point(float(e),float(s))
        bb1=BoundingBox(pnw,pse)

        nw, se = options.bb2.split('|')
        w, n = nw.split(',')
        e, s = se.split(',')
        pnw=Point(float(w),float(n))
        pse=Point(float(e),float(s))
        bb2=BoundingBox(pnw,pse)
        
        i = bb1.intersection(bb2)
        if i is None:
            print 'No intersection'
        else:
            print 'nw: %s se: %s' % (i.nw, i.se)

if __name__ == "__main__":
    main()
