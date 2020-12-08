# ASETUAPI

This is application is an integration with Aarogya Setu OpenAPI which allows you track your employees' COVID status and keep them safe.

## Instructions

We will be using AWS CDK to deploy our application stack. This will require you to install a few dependencies and tools, if you already have any of these installed please continue with the next step.

1. Install all the pre-requisites for building and deploying cdk apps - https://cdkworkshop.com/15-prerequisites.html
2. Install python - https://cdkworkshop.com/15-prerequisites/600-python.html

Note: For ease of demonstration and best experience this workshop assumes you have a user with Administrator access. You can configure more restrictive permissions for your user as required.

Download or clone the repo and open a terminal inside it. Change the placeholders inside `secrets.json` with the actual values. Then follow the below steps to deploy your application.

```Bash
mkdir client/out
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
python create-dependency-layer.py
cdk deploy -y asetuapi
python update-api-secret.py
python generate-exports.py
cdk deploy -y asetuapifrontend
```

These commands perform operations equivalent to the follwing steps. You can paste the commands directly or make the changes yourself.

1. Clone or download this repository to directory and open it in terminal.
2. `mkdir client/out` - This creates an empty placeholder directly for the frontend application build files. The cdk application cannot build without this directory being present.
3. `python3 -m venv .env`  - Create a new virtual environnment to install dependencies. This creates a .env directory.
4. Activate the environment. If you're on Mac or Linux use `source .env/bin/activate`. If you're on windows use `.env\Scripts\activate.bat`
5. Install the required libraries using `pip install -r requirements.txt`
6. Run `python create-dependency-layer.py`, this will install and package dependencies needed for the lambda functions in to zip file. CDK will use the zip file to create a Lambda layer.
6. Fill the placeholders in `secrets.json` with the values from your Aarogya Setu OpenAPI portal.
7. Bootstrap resources in your account so that cdk can deploy the application. `cdk bootstrap`. This is required only once for an account and region.
8. Deploy backend using `cdk deploy asetuapi -y`. This command will deploy the backend infrastructure for the application.
9. Values from the infrastructure are needed to build the deploy the frontend application. Run `python generate-exports.py`, this will fetch the values from cloudformation exports and write them to `client/aws-exports.js`.
10. The cdk app also creates a secret in the AWS Secrets Manager but it does not put the api secret values in it. Run `python put-api-secret-value.py` to put values from `secrets.json` into AWS Secrets Manager.
10. Build the frontend application using `npm install --prefix client && npm run build --prefix client`
11. Deploy the fronted using `cdk deploy asetuapifrontend -y`. Open the `asetuapifrontend.appurl` to access the web page.
12. VOILA! You can now ensure your employees are safe and sound.
