# Tools for working with Google Prediction API

To authenticate, train, check, and predict a model, here are the steps. The `geomancer/CALocsForPrediction.csv` file is up on Google Cloud Storage. 

Note: You need to add a file called `googlekey` to this directory with the [Geomancer Simple API Access Key](https://code.google.com/apis/console/b/0/#project:1077648189165:access) for server apps. This won't work without it, but don't add to the repo since it's a secret, hhh.


```bash
$ java -cp oacurl-1.3.0.jar com.google.oacurl.Login --scope https://www.googleapis.com/auth/prediction
$ ./oauth-train.sh loctype geomancer/CALocsForPrediction.csv
$ ./oauth-check-training.sh loctype
$ ./oauth-predict.sh loctype "'5 miles west berkeley'"
```
