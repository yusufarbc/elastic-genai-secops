# Build from the repository root: docker build -f services/case-service/Dockerfile .
FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY libs/go-common libs/go-common
COPY services/case-service services/case-service
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build     CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/case-service ./services/case-service/cmd

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/case-service /case-service
USER nonroot:nonroot
ENTRYPOINT ["/case-service"]
