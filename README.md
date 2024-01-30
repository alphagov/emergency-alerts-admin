# emergency-alerts-admin

GOV.UK Emergency Alerts admin application - https://admin.emergency-alerts.service.gov.uk/

 - Register and manage users
 - Create and manage services
 - Author and approve emergency alerts

## Setting up to run the Admin UI Server locally

### Local Development Environment Setup
Ensure that you have first followed all of the local development environment setup steps, that can be found [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/221216772/Local+Development+Environment+Setup+-+Updated+instructions), before attempting to run the Admin UI Server locally.

### Python version

You can find instructions on specifying the correct Python version [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/192217089/Setting+up+Local+Development+Environment#Setting-Python-Version).

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

The instructions on setting up the `environment.sh` file can be found [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/192217089/Setting+up+Local+Development+Environment#Getting-Admin-UI-setup).

## Running the Admin and Api services with Postgres

Please refer to the README in the /emergency-alerts-tooling repository, in the /emergency-alerts-tooling/compose folder.

### A note on Webauthn relying party URL

For webauthn to work, the relying party URL must be equal to the domain, or be equal to a registrable sub-domain.  The lower environments, preview and staging, have URLs matching the Route 53 DNS entries. However, production is a special case, so in /emergency-alerts-admin/app/webauthn_server.py, the production URL is defined as a sub-domain to prevent environment names being prefixed to the URL as with the lower environments.

## To run the application

The instructions for running the Admin UI Server can be found [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/192217089/Setting+up+Local+Development+Environment#Run-the-Admin-UI-Server).

Any Python code changes you make should be picked up automatically in development. If you're developing JavaScript code, run `npm run watch` to achieve the same.

## To test the application

Current instructions for unit tests can be found [here](https://gds-ea.atlassian.net/wiki/spaces/EA/pages/192217089/Setting+up+Local+Development+Environment#Running-the-Unit-Tests).

To continuously run js tests, run `npm run test-watch`.

To run a specific JavaScript test, you'll need to copy the full command from `package.json`.

## Further docs

- [Working with static assets](docs/static-assets.md)
- [JavaScript documentation](https://github.com/alphagov/notifications-manuals/wiki/JavaScript-Documentation)
- [Updating dependencies](https://github.com/alphagov/notifications-manuals/wiki/Dependencies)
