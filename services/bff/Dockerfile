# Build from the repository root: docker build -f services/bff/Dockerfile .
FROM golang:1.27-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY libs/go-common libs/go-common
COPY services/bff services/bff
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build     CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/bff ./services/bff/cmd

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/bff /bff
USER nonroot:nonroot
ENTRYPOINT ["/bff"]
