# What is Geomancer?

Geomancer is a web service API that rides on [Google App Engine](https://developers.google.com/appengine/) for geocoding localities using the [point-radius method](http://herpnet.org/herpnet/documents/wieczorek.pdf). Basically it converts a description of a place, like "5 miles west of Berkeley", into coordinates, a bounding box, and an uncertainty value.

# Rationale

Over the past 250 years, scientists have collected specimens describing life on Earth. These results are an irreplaceable archive of global biodiversity. They play a fundamental role in generating new knowledge and guiding conservation decisions. Yet over a billion specimen records remain unusable becuase they aren't geocoded.

# Quick example

The API request to geocode "5 miles west of Berkeley, CA":

`/api/georef?q=5 miles west of Berkeley, CA`

That returns a JSON response:

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

