# What is Geomancer?

Over the past 250 years, biologists have gone into the field to collect specimens documenting the range of life on Earth. The results of these explorations are an irreplaceable archive of global biodiversity. They play a fundamental role in generating new knowledge and guiding conservation decisions. 

Yet, roughly one billion specimen records remain unusable in their current form, simply becuase their localities (descriptions of where they were collected) aren't geocoded into spatial coordinates.

Geomancer is a web service API that rides on [Google App Engine](https://developers.google.com/appengine/) for georeferencing localities using the [point-radius method](http://herpnet.org/herpnet/documents/wieczorek.pdf). Basically it converts a description of a place, like "5 miles west of Berkeley", into a geocoded location with coordinates, a bounding box, and an uncertainty value.

For example, to get georeferences for "5 miles west of Berkeley, CA":

`/api/georef?q=5 miles west of Berkeley, CA`

Which would return the following JSON response. Note that `georefs` contains the uncertainty and a list of [GeoJSON](http://www.geojson.org/geojson-spec.html) point features:

```json
{
  "location":{
    "name":"5 miles west of berkeley, ca"
  },
  "georefs":[
    {
      "uncertainty":14366.0,
      "feature":{
        "geometry":{
          "type":"Point",
          "coordinates":[
            -122.372044,
            37.876012699999997
          ]
        },
        "type":"Feature",
        "bbox":[
          -122.48779690000001,
          37.784700600000001,
          -122.25657750000001,
          37.967211800000001
        ]
      }
    }
  ]
}
```

# Features (TODO)

### Types of localities

### Language translation

### CartoDB

### Bulk georeferencing

### Result types
# Motivation

Georeferenced biocollection data is in high demand. Mapping species occurrence data is fundamental to describing and analysing biotic distributions. This information is also critical for conservation planning, reserving selection, monitoring, and the examination of the potential effects of climate change on biodiversity. 

Increasing the availability of georeferenced species distribution data will vastly increase our ability to understand patterns of biodiversity and to make balanced conservation-related decisions. Most data in these analyses come from natural history collections, which provide unique and irreplaceable information, especially for areas that have undergone habitat change due to clearing for agriculture or ubanization. 

The BioGeomancer research consortium is coordinated by the University of California at Berkeley and is developing a universal system for georeferencing the diverse specimen records in natural history collections.
