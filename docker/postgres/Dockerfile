FROM golang:1.26.5-alpine3.24@sha256:0178a641fbb4858c5f1b48e34bdaabe0350a330a1b1149aabd498d0699ff5fb2 AS gosu-build

RUN CGO_ENABLED=0 GOBIN=/out \
    go install github.com/tianon/gosu@6456aaa0f3c854d199d0f037f068eb97515b7513

FROM postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193

COPY --from=gosu-build /out/gosu /usr/local/bin/gosu
RUN chmod 0755 /usr/local/bin/gosu \
    && gosu nobody true

USER postgres
