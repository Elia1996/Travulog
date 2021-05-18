#!/bin/bash

cat ./test/arch/htv_pkg.tvt | sed s/BASEDIR/$(pwd | sed 's/\//\\\//g')/g > ./test/arch/htv_pkg.tv
