#!/bin/bash

if [ "!" -d mcp23017 ]
then
    echo "Must be run in project home."
    exit 255
fi

rm -R -f doc/*

. .virtualenv.$(hostname -s)/bin/activate 

PYTHONPATH=. pdoc -n -o doc/ -d google \
             --no-include-undocumented \
             --no-search \
             mcp23017.mcp23017
