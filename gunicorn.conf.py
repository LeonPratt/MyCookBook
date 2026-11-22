import os

bind = f"{os.getenv('COOKBOOK_HOST', '0.0.0.0')}:{os.getenv('COOKBOOK_PORT', '5432')}"
workers = int(os.getenv("COOKBOOK_WORKERS", "1"))
threads = int(os.getenv("COOKBOOK_THREADS", "2"))
worker_class = "gthread"
timeout = 60
max_requests = 500
max_requests_jitter = 50
accesslog = "-"
errorlog = "-"
capture_output = True
control_socket_disable = True
