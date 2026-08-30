# Build image for the backend package. Run from repo root with:
#   yarn install --immutable && yarn tsc && yarn build:backend && yarn build-image
# Host Node version must match the FROM image below — mismatches break
# native modules. See https://backstage.io/docs/deployment/docker#multi-stage-build

FROM node:24-trixie-slim

# sqlite3 deps — skip if unused, and move better-sqlite3 to devDependencies.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

USER node

# Needs BuildKit (DOCKER_BUILDKIT=1) so /app is created as `node`, not root.
WORKDIR /app

COPY --chown=node:node .yarn ./.yarn
COPY --chown=node:node .yarnrc.yml ./
COPY --chown=node:node backstage.json ./

ENV NODE_ENV=production

# Skeleton (each package.json) copied first so yarn install caches independently of source changes.
COPY --chown=node:node yarn.lock package.json packages/backend/dist/skeleton.tar.gz ./
RUN tar xzf skeleton.tar.gz && rm skeleton.tar.gz

RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn workspaces focus --all --production && rm -rf "$(yarn cache clean)"

COPY --chown=node:node examples ./examples

COPY --chown=node:node packages/backend/dist/bundle.tar.gz app-config*.yaml ./
RUN tar xzf bundle.tar.gz && rm bundle.tar.gz

CMD ["node", "packages/backend", "--config", "app-config.yaml", "--config", "app-config.production.yaml"]
