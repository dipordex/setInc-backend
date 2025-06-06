# Project CI/CD

## Architecture

Project is run in docker containers (distributed by services: back end app, worker, etc).
There is a base image, from which inherits every service container.

There are 3 deployment environments:
- development/testing
- staging
- production

Every environment build/deployment is triggered by git pushes into Gitlab to its according branch. Development is built from `dev` branch, staging is built from `stage` branch & production is built from `master` branch. Git tags are not utilized in the process.

All related files are placed in `.deploy` folder in project root. Every environment has its own folder with the configuration files.

Drone.io is used for the pipelines & all configuration is initiated in `.drone.yml`.

## Variables

All variables that end up on the deployed service are inside environment folder, `.env` file.

Please note: for `False` values use empty string (e.g. `DEBUG=`). In bash, the "False" string (e.g. `DEBUG=False`) will render as `True`.

## AWS

The current configuration is enabled for ECS deployment. While service & tasks are created automatically, you still need to configure these (depending on what's used):
- IAM users for all AWS resources
- ECR repo
- S3 buckets
- SES domains
- EC2 ECS-enabled instances
- EC2 ELBs & Target groups

## Deployment

After AWS is set up and the project is enabled on Drone.io, CD process should start working automatically.
