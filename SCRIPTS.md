API:-
cd api
uv run flask run --host 0.0.0.0 --port=5001 --debug

Middleware:-
cd api
uv run celery -A app.celery worker -P gevent -c 1 --loglevel INFO -Q dataset,generation,mail,ops_trace

WEB:-
cd web
pnpm start

pnpm build

Plugin Services:-
go run cmd/server/main.go

Docker:-
cd docker
sudo docker compose up -d