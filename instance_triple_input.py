#!/usr/bin/python3

from htravulog import *
import re

filename = "instanza_da_triplicare.sv"

fp = open(filename, "r")
data = fp.read()
data_split = data.split("\n")

for line in data_split:
    if re.match(r".*\_i\W.*", line) != None:
        lista = SplitInstanceLine(line)
        print("    ." + "{:<20}".format(lista[0]) + "( {" + "{:<60}".format(lista[1]+", "+lista[1]+", "+lista[1] ) + " } )," )
    else:
        print(line)

