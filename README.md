# Randomall tg bot

## Requirements
- `RabbitMQ`
- `Docker`

## Deployment

```sh
docker build -t <tag> .

# specify port, network, env, etc...
docker run ... <tag>
```

## Configuration

You can configure the application with the following environment variables:

- **`DEBUG`**: One of `0` or `1`.

	Default: `1`

- **`TELEGRAM_API_TOKEN`**: Telegram bot API token.

- **`TELEGRAM_WEBHOOK_HOST`**: HTTP host.

- **`TELEGRAM_WEBHOOK_PORT`**: HTTP port.

	Default: `5001`.

- **`TELEGRAM_WEBHOOK_PATH`**: HTTP path.

- **`MQ_URL`**: amqp connection string, used to connect to RabbitMQ.

	Format: `amqp://<username>:<password>@<host>:<port>/<vhost>`.