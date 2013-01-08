#!/bin/bash
# Check training status of a prediction model.
# Usage: oauth-training.sh MODEL_ID

ID=$1
KEY=`cat googlekey`

# Check training status.
java -cp ./oacurl-1.3.0.jar com.google.oacurl.Fetch -X GET \
  "https://www.googleapis.com/prediction/v1.5/trainedmodels/$ID?key=$KEY"
echo