# Tools for working with Google Prediction API

To authenticate, train, check, and predict a model, here are the steps. The `geomancer/CALocsForPrediction.csv` file is up on Google Cloud Storage.


```bash
$ java -cp oacurl-1.3.0.jar com.google.oacurl.Login --scope https://www.googleapis.com/auth/prediction
$ ./oauth-train.sh loctype geomancer/CALocsForPrediction.csv
$ ./oauth-check-training.sh loctype
$ ./oauth-predict.sh loctype "'5 miles west berkeley'"
```
