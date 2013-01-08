#!/bin/bash
# Run a prediction against a model.
# Usage: oauth-predict.sh MODEL_ID DATA

ID=$1
INPUT="$2"
KEY=`cat googlekey`
data="{\"input\" : { \"csvInstance\" : [ $INPUT ]}}"

java -cp ./oacurl-1.3.0.jar com.google.oacurl.Fetch -X POST \
-t JSON \
"https://www.googleapis.com/prediction/v1.5/trainedmodels/$ID/predict?key=$KEY" <<< $data
echo