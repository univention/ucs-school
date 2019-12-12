#!/bin/sh

SOURCES="modules/ucsschool/lib/tests"

isort --apply --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --recursive --project ucsschool --project udm_rest_client --project univention $SOURCES

black --target-version py37 $SOURCES
