#!/usr/bin/env python
# encoding: utf-8

import sys
import re
import json

fileName = sys.argv[1]
strPropertyDict = sys.argv[2]

print(strPropertyDict)

with open(fileName, "w") as f:
    propertyDict =json.loads(strPropertyDict)
    for pKey, pValue in propertyDict.items():
        f.write("%s = %s \n"%(pKey,pValue))
