# ASGI Demo 🚀

[![Built with Cookieplone](https://img.shields.io/badge/built%20with-Cookieplone-0083be.svg?logo=cookiecutter)](https://github.com/plone/cookieplone-templates/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/simplesconsultoria/asgi-demo/actions/workflows/main.yml/badge.svg)](https://github.com/simplesconsultoria/asgi-demo/actions/workflows/main.yml)

A demo of ASGI with Plone and Volto: a live Breaking News page.

Open a story and its updates arrive as they are published, without a reload.
The page is served by Plone on [ploneasgi](https://github.com/simplesconsultoria/ploneasgi),
which holds each reader's websocket on the event loop instead of a worker thread.

## How it works 🛰️

-   **Content.** A `BreakingNews` story is a folder of `BreakingNewsUpdate` items.
    The example content adds the story *Brazil Elections 2026* at `/brazil-2026`,
    with 43 updates and the 10 images they use from `/images`.
-   **Storage.** The ZODB lives in PostgreSQL 18 through `zodb-pgjsonb`, with every
    blob in S3 ([silo](https://github.com/pgsty/silo)). The catalog is
    `plone.pgcatalog`.
-   **Publishing.** When an update is added, its message is written to an outbox
    table in the same PostgreSQL transaction as the content, followed by a
    `NOTIFY`. PostgreSQL delivers the notification only if that transaction
    commits, so readers never see an update that was rolled back.
-   **Fan-out.** Each backend `LISTEN`s once and forwards each message to its own
    readers. With two backends behind Traefik, an update saved on one reaches the
    readers on both. Each backend also reports its reader count, and the page shows
    the total.
-   **Access.** A reader may open a story's socket only if they may view the story,
    checked by traversing to it with their own permissions. Private stories, and
    stories inside sections the reader cannot enter, are refused.
-   **Reconnecting.** The page reconnects with a jittered backoff, and asks for
    the updates it missed while it was away.

## Quick Start 🏁

### Prerequisites ✅

-   An [operating system](https://6.docs.plone.org/install/create-project-cookieplone.html#prerequisites-for-installation) that runs all the requirements mentioned.
-   [uv](https://6.docs.plone.org/install/create-project-cookieplone.html#uv)
-   [nvm](https://6.docs.plone.org/install/create-project-cookieplone.html#nvm)
-   [Node.js and pnpm](https://6.docs.plone.org/install/create-project.html#node-js) 24
-   [Make](https://6.docs.plone.org/install/create-project-cookieplone.html#make)
-   [Git](https://6.docs.plone.org/install/create-project-cookieplone.html#git)
-   [Docker](https://docs.docker.com/get-started/get-docker/) (optional)


### Installation 🔧

1.  Clone this repository, then change your working directory.

    ```shell
    git clone git@github.com:simplesconsultoria/asgi-demo.git
    cd asgi-demo
    ```

2.  Install this code base.

    ```shell
    make install
    ```


### Fire Up the Servers 🔥

The backend needs PostgreSQL and silo, which run in Docker.

1.  Start PostgreSQL on port 5432 and silo on port 9000 (console on 9001).
    `make install` already does this.

    ```shell
    make backend-services-start
    ```

2.  Create a new Plone site on your first run. `make install` already does this
    too.

    ```shell
    make backend-create-site
    ```

3.  Start the backend at http://localhost:8080/.

    ```shell
    make backend-start
    ```

4.  In a new shell session, start the frontend at http://localhost:3000/.

    ```shell
    make frontend-start
    ```

Then open http://localhost:3000/brazil-2026. 🎉

Volto's development proxy does not forward websockets, so in development the page
connects straight to the backend, at `ws://localhost:8080/++asgi++`. Set
`BREAKING_NEWS_SOCKET_BASE` when starting the frontend to use another address.

To stop PostgreSQL and silo, run `make backend-services-stop`. To start over with
an empty database, run `make -C backend services-remove-data`.

### Local Stack Deployment 📦

Deploy a local Docker Compose environment that includes the following.

- Docker images for Backend and Frontend 🖼️
- A Traefik router, two Plone backends, PostgreSQL 18 and silo 🗃️
- Accessible at [http://asgi-demo.localhost](http://asgi-demo.localhost) 🌐

Run the following command in a shell session.

```shell
make stack-start
```

On the first run, a one-off `backend-init` service creates the site with its
example content and switches its catalog to `plone.pgcatalog`, before the
backends start. Then open http://asgi-demo.localhost/brazil-2026. 🚀

To remove the stack and its data, run `make stack-rm`.

## Project structure 🏗️

This monorepo consists of the following distinct sections:

- **backend**: Houses the API and Plone installation, utilizing pip instead of buildout, and includes a policy package named asgidemo.
- **frontend**: Contains the React (Volto) package.
- **devops**: Encompasses Docker stack, Ansible playbooks, and cache settings.
- **docs**: Scaffold for writing documentation for your project.

### Why this structure? 🤔

- All necessary codebases to run the site are contained within the repository (excluding existing add-ons for Plone and React).
- Specific GitHub Workflows are triggered based on changes in each codebase (refer to .github/workflows).
- Simplifies the creation of Docker images for each codebase.
- Demonstrates Plone installation/setup without buildout.

## Code quality assurance 🧐

To check your code against quality standards, run the following shell command.

```shell
make check
```

### Format the codebase

To format and rewrite the code base, ensuring it adheres to quality standards, run the following shell command.

```shell
make format
```

| Section | Tool | Description | Configuration |
| --- | --- | --- | --- |
| backend | Ruff | Python code formatting, imports sorting  | [`backend/pyproject.toml`](./backend/pyproject.toml) |
| backend | `zpretty` | XML and ZCML formatting  | -- |
| frontend | ESLint | Fixes most common frontend issues | [`frontend/.eslintrc.js`](.frontend/.eslintrc.js) |
| frontend | prettier | Format JS and Typescript code  | [`frontend/.prettierrc`](.frontend/.prettierrc) |
| frontend | Stylelint | Format Styles (css, less, sass)  | [`frontend/.stylelintrc`](.frontend/.stylelintrc) |

Formatters can also be run within the `backend` or `frontend` folders.

### Linting the codebase
or `lint`:

 ```shell
make lint
```

| Section | Tool | Description | Configuration |
| --- | --- | --- | --- |
| backend | Ruff | Checks code formatting, imports sorting  | [`backend/pyproject.toml`](./backend/pyproject.toml) |
| backend | Pyroma | Checks Python package metadata  | -- |
| backend | check-python-versions | Checks Python version information  | -- |
| backend | `zpretty` | Checks XML and ZCML formatting  | -- |
| frontend | ESLint | Checks JS / Typescript lint | [`frontend/.eslintrc.js`](.frontend/.eslintrc.js) |
| frontend | prettier | Check JS / Typescript formatting  | [`frontend/.prettierrc`](.frontend/.prettierrc) |
| frontend | Stylelint | Check Styles (css, less, sass) formatting  | [`frontend/.stylelintrc`](.stylelintrc) |

Linters can be run individually within the `backend` or `frontend` folders.


## Internationalization 🌐

Generate translation files for Plone and Volto with ease:

```shell
make i18n
```

## Credits and acknowledgements 🙏

Generated using [Cookieplone (2.0.2)](https://github.com/plone/cookieplone) and [cookieplone-templates (cccf30f)](https://github.com/plone/cookieplone-templates/commit/cccf30f64531530f662d9b8fb326ea1eb465b380) on 2026-10-27 15:31:53.843613. A special thanks to all contributors and supporters!
