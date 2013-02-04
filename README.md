# What is Geomancer?

Geomancer is a web service API (in private beta) that rides on [Google App Engine](https://developers.google.com/appengine/) for geocoding localities using the [point-radius method](http://herpnet.org/herpnet/documents/wieczorek.pdf). Basically it converts a description of a place, like "5 miles west of Berkeley", into coordinates, a bounding box, and an uncertainty value.

# Rationale

Over the past 250 years, scientists have collected specimens describing life on Earth. These results are an irreplaceable archive of global biodiversity. They play a fundamental role in generating new knowledge and guiding conservation decisions. Yet over a billion specimen records remain unusable becuase they aren't geocoded.

# Parameters

The API accepts the following parameters. Values must be URL encoded.

<table>
  <tr>
    <td><b>Parameter</b></td>
    <td><b>Description</b></td>
    <td><b>Example</b></td>
  </tr>
  <tr>
    <td>q</td>
    <td>The query to geocode.</td>
    <td>q=chengdu, china</td>
  </tr>
  <tr>
    <td>cb</td>
    <td>Callback function name for JSONP.</td>
    <td>cb=myCb</td>
  </tr>
  <tr>
    <td>l</td>
    <td><a href='http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes'>ISO 639-1</a> language code of the query.</td>
    <td>l=zh</td>
  </tr>
  <tr>
    <td>f</td>
    <td>Result format can be csv, verbose, or empty for default JSON.</td>
    <td>f=verbose</td>
  </tr>
  <tr>
    <td>cdb*</td>
    <td>Write geocodes to CartoDB by specifying a "user,table,apikey" triple.</td>
    <td>cdb=aaron,my-table,my-apikey</td>
  </tr>  
</table>

_* Your CartoDB table needs to exist with name, longitude, latitude, and uncertainty columns. Don't forget to [georeference](http://developers.cartodb.com/tutorials/how_to_georeference.html#georeference) your longitude and latitude in CartoDB so they show up on the map!_

# Examples

We're in private beta, so ping [@eightysteele](http://github.com/eightysteele) if you want to help us test the API!

### 5 miles west of berkeley, ca

http://beta.geomancer-api.appspot.com/api/georef?q=5%20miles%20west%20of%20berkeley,%20ca

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

### 5 millas al oeste de berkeley, ca

http://beta.geomancer-api.appspot.com/api/georef?q=5%20millas%20al%20oeste%20de%20Berkeley,%20CA&l=es

### 5 miles west of berkeley, ca (JSONP)

http://beta.geomancer-api.appspot.com/api/georef?q=5%20miles%20west%20of%20berkeley,%20ca&cb=myCb
