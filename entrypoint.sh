# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
        echo "Trapped CTRL-C, exiting ..."
	exit 0
}

case "$ENV" in
	"dev")
		echo "Running in Dev Mode"
		bash
	;;
	"ingest")
		echo "Running Ingestion Script"
		python3 ./ingest.py
	;;
	"*" | "prod")
		echo "Running in Prod Mode"
		redis-server --daemonize yes
		rqworker --verbose &
		gunicorn -c ./gunicorn.conf.py app:app
	;;
esac
