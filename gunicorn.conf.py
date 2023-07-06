# Gunicorn configuration file
import multiprocessing

max_requests = 100
max_requests_jitter = 50

log_file = "-"
log_level = "debug"
accesslog = "-"
errorlog = "-"

bind = "0.0.0.0:50505"

#workers = (multiprocessing.cpu_count() * 2) + 1
workers = 4
threads = workers
timeout = 60
