#!/usr/bin/ksh

git ls-remote --sort='version:refname' --tags /ms/dev/aquilon/aqd/SCM/aqd.git | grep refs/tags/TRAIN_DIST_aquilon/aqd | tail -n 2 | head -n 1 | awk '{print $2}' | sed 's/^\([^/]\+\/\)\{2\}//' > doc/version.txt
msdlbuild clean
make clean
make install
msdlbuild metadata