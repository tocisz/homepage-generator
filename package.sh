#!/usr/bin/env bash
update_package() {
  rm -rf python lib-layer.zip
  pip install -r requirements.txt --target python/lib/python3.7/site-packages
  zip -r9 lib-layer.zip python
}

create_zip() {
  rm lambda.zip
  cp config-lambda.json config.json
  zip lambda.zip *.py config.json
  cp config-local.json config.json
}

if [ "$1" == "update" ]
then update_package
else create_zip
fi
