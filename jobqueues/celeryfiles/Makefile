start-rabbit:
	docker run -d -p 5462:5672 rabbitmq

stop-rabbit:
	docker rm $$(docker stop $$(docker ps -a -q --filter ancestor=rabbitmq --format="{{.ID}}"))