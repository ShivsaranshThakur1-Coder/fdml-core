#!/usr/bin/env bash
set -euo pipefail
echo "== fdml version =="; fdml --help | head -n 3
echo "== make ci =="; make -s ci
echo "== make json =="; make -s json; ls -1 out/json | wc -l
echo "== make html =="; make -s html; ls -1 out/html | wc -l
rm -f /tmp/smoke.fdml.xml
fdml init /tmp/smoke.fdml.xml --title "Smoke" --meter 3/4 --tempo 96 --figure-id f-1 --figure-name Intro
fdml validate /tmp/smoke.fdml.xml
echo "OK"
