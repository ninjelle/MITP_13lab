FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o search-agent .

# ── Финальный образ ──
FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/search-agent .

ENV NATS_URL=nats://nats:4222

CMD ["./search-agent"]
