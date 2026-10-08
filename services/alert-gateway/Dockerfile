# Build from the repository root: docker build -f services/alert-gateway/Dockerfile .
FROM golang:1.27-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY libs/go-common libs/go-common
COPY services/alert-gateway services/alert-gateway
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build     CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/alert-gateway ./services/alert-gateway/cmd

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/alert-gateway /alert-gateway
USER nonroot:nonroot
ENTRYPOINT ["/alert-gateway"]
