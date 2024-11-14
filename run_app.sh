PORT=7015

redis-server --port 6380 --daemonize yes
uvicorn app:app --port $PORT --host 0.0.0.0