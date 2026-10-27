# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.14
FROM plone/server-builder:uv-${PYTHON_VERSION} AS builder

COPY . /src
WORKDIR /src

# Install package
RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=mx.ini,target=mx.ini \
    uv tool run mxdev[uv] -c mx.ini && \
    uv sync \
        --no-dev \
        --no-group test \
        --group container \
        --no-editable

# Move skeleton files to /app
RUN <<EOT
    mv /app_skeleton/* /app
    rm -Rf /app_skeleton
    chmod +x /app/docker-entrypoint.sh
    mv scripts/create_site.py /app/scripts/create_site.py
    mv scripts/enable_pgcatalog.py /app/scripts/enable_pgcatalog.py
EOT

# Serve with ploneasgi under uvicorn instead of runwsgi under waitress. The
# entrypoint keeps choosing the zope.conf from the environment (here, PGJsonb
# with S3 blobs); only the command that serves it changes. The grep fails the
# build if a new base image no longer has the line being replaced.
RUN <<"EOT"
    set -e
    sed -i 's|^  exec \$sudo \$VENVBIN/runwsgi -v etc/zope.ini config_file=\${CONF}$|  export PLONE_ZOPE_CONF=etc/${CONF}\n  exec $sudo $VENVBIN/python -m asgidemo.server|' /app/docker-entrypoint.sh
    grep -q 'exec $sudo $VENVBIN/python -m asgidemo.server' /app/docker-entrypoint.sh
    ! grep -q 'runwsgi -v etc/zope.ini' /app/docker-entrypoint.sh
EOT

# Compile translation files
RUN <<EOT
    /app/bin/python /compile_mo.py
EOT

FROM plone/server-prod-config:uv-${PYTHON_VERSION}

LABEL maintainer="Érico Andrei <ericof@plone.org>" \
      org.label-schema.name="asgi-demo-backend" \
      org.label-schema.description="ASGI Demo backend image." \
      org.label-schema.vendor="Érico Andrei"

# Copy the pre-built `/app` directory to the runtime container
# and change the ownership to user app and group app in one step.
COPY --from=builder --chown=500:500 /app /app

RUN <<EOT
    ln -s /data /app/var
    chown -R 500:500 /data
EOT
