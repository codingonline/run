for line in $(ifconfig | grep veth | awk '{print $1}')
do
    ifconfig $line down;
done
ifconfig | grep veth | awk '{print $1}'
service docker restart
docker rm `docker ps -a -q`
docker -H tcp://0.0.0.0:9375 rm `docker -H tcp://0.0.0.0:9375 ps -a -q`
/bin/bash /root/scripts/swarm.sh
echo 'starting services...'
sleep 10
python /root/core/start.py
