FROM golang:latest AS builder
ENV GOTOOLCHAIN=auto
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go mod tidy && go build -o search-agent .

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /app/search-agent .
ENV NATS_URL=nats://nats:4222
CMD ["./search-agent"]