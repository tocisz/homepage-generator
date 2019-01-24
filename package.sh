#!/usr/bin/env bash
update_package() {
  rm -rf package
  pip install -r requirements.txt --target package
}

create_zip() {
  rm lambda.zip
  cd package
  zip -r9 ../lambda.zip .
  cd ..
  cp config-lambda.json config.json
  zip -g lambda.zip *.py config.json
  cp config-local.json config.json
}

if [ $1 == "update" ]
then update_package
else create_zip
fi
