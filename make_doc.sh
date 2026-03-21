#!/bin/bash

if [ "!" -f mcp23017.py ]
then
    echo "Must be run in project home."
    exit 255
fi

rm -f doc/*

PYTHONPATH=. pdoc -n -o doc/ -d google \
             --no-include-undocumented \
             --no-search \
             mcp23017
