# Developing

## Getting the code

Make sure you have Git installed, and then from the command line:

```bash
$ git clone git@github.com:GeomancerProject/geomancer-api.git
```

That will download the full code repository into a directory named `geomancer-api`.

## Dev server

The Geomancer API rides on [Google App Engine](https://developers.google.com/appengine) Python 2.7 runtime, so you'll need to [download and install](https://developers.google.com/appengine/downloads) the latest Python SDK. 

It's useful adding the SDK to your PATH by adding the following line to your `~/.bashrc` or `~/.bash_profile`:

```bash
export PATH=$PATH:/your/path/to/google_appengine_sdk
```

App Engine ships with a local development server. At the command line:

```bash
$ cd geomancer-api
$ dev_appserver.py --clear_search_index --high_replication --use_sqlite -c .
```

Boom! It's now running locally at [http://localhost:8080](http://localhost:8080) and you get an admin console at [http://localhost:8080/_ah/admin](http://localhost:8080/_ah/admin).
