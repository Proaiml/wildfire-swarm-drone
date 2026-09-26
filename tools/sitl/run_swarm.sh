#!/bin/bash
# Starts COUNT ArduCopter SITL instances side by side near the base station.
# Instance i: TCP 5760+10*i, SYSID_THISMAV=i+1, home shifted ~25 m east per instance.
COUNT=${COUNT:-3}
LAT=${LAT:-37.05637}
LON=${LON:-30.79052}
ALT=${ALT:-30}
cd /ardupilot
for ((i = 0; i < COUNT; i++)); do
    lon=$(python3 -c "print(${LON} + ${i} * 0.00028)")
    mkdir -p /sitl/$i && cd /sitl/$i
    printf 'SYSID_THISMAV %d\nFS_GCS_ENABLE 1\nFS_GCS_TIMEOUT 5\nRTL_ALT 3000\nFENCE_ENABLE 0\n' $((i + 1)) > sysid.parm
    /ardupilot/build/sitl/bin/arducopter -S --model + --speedup 1 -I${i} \
        --defaults /ardupilot/Tools/autotest/default_params/copter.parm,/sitl/$i/sysid.parm \
        --home ${LAT},${lon},${ALT},0 > /sitl/$i/sitl.log 2>&1 &
    echo "SITL $i: tcp:127.0.0.1:$((5760 + 10 * i))  sysid $((i + 1))  home ${LAT},${lon}"
done
wait
