# Pre-Requirements
## Setup Qdrant cloud
1. Sign-in or sign-up at [Qdrant Cloud](https://cloud.qdrant.io/)
1. Create a free 1GB cluster
1. Note down the Qdrant API key and the Qdrant Cluster Url

## Setup OpenAI
1. Sign-in or sign-up at [OpenAI](https://openai.com/)
1. Setup your account with enough credits
1. Note down the OpenAI API key

## Slack Bot App setup
1. You need to be a Slack admin for your workspace. 
1. Go to [Slack apps](https://api.slack.com/apps) and click on “Create a new app”, select “From scratch” in the popup window, and choose a name (for me, it is “PlivoAskMe”), then click on “Create App”.
1. Click on “New Slack Commands” and point it to your application API hosted on fly.io (you can do that later if the fly.io application is not online yet)
1. From the left menu, click on “OAuth & Permissions” then in the “Bot Token Scopes” section, click on “Add an Oauth scope” and select “commands”
1. Go back to the “Basic information” section in the left menu and click “Install to workspace”
1. You should be able to see the “App Credentials” section.
1. Note down the Slack "Verification Token"

## Applicaiton settings
Copy the settings.py example file
```bash
cp settings.py.example settings.py
```

Edit and configure the following variables:
- INGEST_GIT_REPO_URLS
- INGEST_SITEMAP_URLS
- INGEST_SITEMAP_URLS_FILTERS

# Fly.io deployment
## Setup the application
Create the application
```bash
fly apps create <app_name>
```

Copy the fly.toml example file
```bash
cp fly.toml.example fly.toml
```

Change the "app" with the <app_name>, and "OPENAI_MODEL" and "VECTOR_DATABASE" settings.


## Configure secrets
```bash
fly secrets QDRANT_API_KEY=xxxx # replace 'xxxx' with your Qdrant API key
fly secrets OPENAI_API_KEY=xxxx # replace 'xxxx' with your OpenAI API key
fly secrets SLACK_TOKEN_ID=xxxx # replace 'xxxx' with your Slack Verification token
```

## Deploy the app and machine
```bash
fly deploy --force-machines --local-only --region iad --vm-size shared-cpu-2x
```

## Append data to the vector database
```bash
fly scale memory 4096 # scale up memory to ingest the data
fly ssh console --pty -C 'python3 /app/ingest.py' # collect and inject data into the vector database
fly scale memory 2048 # scale down memory
```

# Update the app
```bash
fly deploy --local-only
```

