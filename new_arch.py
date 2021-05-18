#!/bin/bash

./htravulog.py

cd out
cp *.sv ../../../cv32e40p/rtl

cd ../../../cv32e40p/rtl
mv cv32e40p_pkg2.sv include/

echo "comment: "
read comment
cd ..
git add -A
git commit -a -m "$comment"
git push

