#!/bin/bash
P=6001
worker=4
host="0.0.0.0"
case "$@" in
    start)
        gunicorn -k gevent -b $host:$P -w $worker flaskrun:app -D
        ;;
    stop)
        kill -9 `ps aux|grep gunicorn|grep $P|awk '{print $2}'|xargs`
        ;;

    restart)
        kill -9 `ps aux|grep gunicorn|grep $P|awk '{print $2}'|xargs`
        sleep 1
        gunicorn -k gevent -b $host:$P -w $worker flaskrun:app -D
        ;;
    reload)
        ps aux |grep gunicorn |grep $P | awk '{print $2}'|xargs kill -HUP
        ;;
    status)
    pids=$(ps aux|grep gunicorn|grep $P)
        echo "$pids"
    ;;
    status2)
    pids=$(ps aux|grep gunicorn|grep $SP)
        echo "$pids"
    ;;
    *)
        echo 'unknown arguments args(start|stop|restart|status|reload)'
        exit 1
        ;;
esac
