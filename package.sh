#!/usr/bin/env bash
rm lambda.zip
cd package
zip -r9 ../lambda.zip .
cd ..
cp config-lambda.json config.json
zip -g lambda.zip *.py config.json
cp config-local.json config.json
