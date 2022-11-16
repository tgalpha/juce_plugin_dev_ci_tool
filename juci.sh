#! /bin/sh

pushd . &> /dev/null

ScriptDir="$( cd "$( dirname "$0")" && pwd)"
cd "$ScriptDir"

python _juci.py "$@"

popd &> /dev/null
