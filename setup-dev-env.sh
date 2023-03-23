#!/bin/ksh
export AQDCONF="etc/aqd.conf.$USER"
export AQHOST=$HOSTNAME
export AQSERVICE=$USER
# should be same as knc port if you want to use the auth
export AQPORT=8900
export AQVER=alpha
export PGKRBSRVNAME=psgdbt
module unload python/core/3.10.4
module load python/core/2.7.18-64

# pytest
export PATH=/ms/dist/python/PROJ/core/2.7.18-0-64/bin:$PATH
export PATH=/ms/dist/python/PROJ/pytest/4.6.3/bin:$PATH
export PATH=/ms/dist/python/PROJ/pylint/1.9.2/bin:$PATH
export PATH=/ms/dist/python/PROJ/bandit/1.6.2/bin:$PATH
export PATH=/ms/dist/sec/PROJ/bandit/2019.12.05-3/bin:$PATH
export PYTHONPATH=lib:tests:$PYTHONPATH

echo "More help here: http://wiki.ms.com/Aquilon/DevelopingTheBroker#How_do_I_run_a_test_broker"
echo -e "\nCreate your aqd.conf file at etc/aqd.conf.$USER and run the broker with ./tests/dev_aqd.sh"
