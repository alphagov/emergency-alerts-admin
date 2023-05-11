# emergency-alerts-admin

GOV.UK Emergency Alerts admin application - https://admin.emergency-alerts.service.gov.uk/

 - Register and manage users
 - Create and manage services
 - Author and approve emergency alerts

## Setting up

### Python version

At the moment we run Python 3.9 in production.

### NodeJS & NPM

If you don't have NodeJS on your system, install it with homebrew.

```shell
brew install node
```

`nvm` is a tool for managing different versions of NodeJS. Follow [the guidance on nvm's github repository](https://github.com/nvm-sh/nvm#installing-and-updating) to install it.

Once installed, run the following to switch to the version of NodeJS for this project. If you don't
have that version, it should tell you how to install it.

```shell
nvm use
```

### `environment.sh`

In the root directory of the application, run:

```
echo "
export NOTIFY_ENVIRONMENT='development'
export ENVIRONMENT='development'
export SERVICE='admin'

export FLASK_APP=application.py
export FLASK_DEBUG=False
export WERKZEUG_DEBUG_PIN=off
"> environment.sh
```

## Running the Admin and Api services with Postgres

Please refer to the README in the /emergency-alerts-tooling repository, in the /emergency-alerts-tooling/compose folder.

## THE FOLLOWING INSTRUCTIONS ARE DEPRECATED AND SHOULD BE USED FOR HISTORICAL REFERENCE ONLY
(This section will be removed in the future, as the Emergency Alerts app is fully decoupled from Notify)

### AWS credentials

To run parts of the app, such as uploading letters, you will need appropriate AWS credentials. See the [Wiki](https://github.com/alphagov/notifications-manuals/wiki/aws-accounts#how-to-set-up-local-development) for more details.

### Pre-commit

We use [pre-commit](https://pre-commit.com/) to ensure that committed code meets basic standards for formatting, and will make basic fixes for you to save time and aggravation.

Install pre-commit system-wide with, eg `brew install pre-commit`. Then, install the hooks in this repository with `pre-commit install --install-hooks`.

## To run the application

```shell
# install dependencies, etc.
make bootstrap

# run the web app
make run-flask
```

Then visit [localhost:6012](http://localhost:6012).

Any Python code changes you make should be picked up automatically in development. If you're developing JavaScript code, run `npm run watch` to achieve the same.

## To test the application

```
# install dependencies, etc.
make bootstrap

# run all the tests
make test

# continuously run js tests
npm run test-watch
```

To run a specific JavaScript test, you'll need to copy the full command from `package.json`.

## Further docs

- [Working with static assets](docs/static-assets.md)
- [JavaScript documentation](https://github.com/alphagov/notifications-manuals/wiki/JavaScript-Documentation)
- [Updating dependencies](https://github.com/alphagov/notifications-manuals/wiki/Dependencies)
