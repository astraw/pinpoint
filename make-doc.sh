#!/bin/bash -x
set -e

git diff --quiet || { echo "aborting - repo not clean. try git status"; exit 1; }

rm -rf /tmp/gh-pages
python setup.py build_sphinx
cp -a docs/build/html /tmp/gh-pages

git checkout gh-pages
git clean -dxf
git rm -r *
cp -a /tmp/gh-pages/* .
touch .nojekyll
find . | xargs git add
git commit -m "update pages"

git checkout master
