#!/bin/bash

state="/home/gio/.local/state/togglemonitorlock"
booleanvalue="false"
cat ${state}
if [[ -f ${state} ]]; then
     booleanvalue=$(cat ${state})
fi

if [[ ${booleanvalue} == "true" ]]; then
     wlr-randr --output DP-3 --pos 2560,0
     echo "false" > ${state}
     dunstify "Cursor Unlocked"
else
     wlr-randr --output DP-3 --pos 3560,0
     echo "true" > ${state}
     dunstify "Cursor Locked"
fi
