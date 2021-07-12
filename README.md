# ASETUAPI

**NOTE: This solution is no longer actively maintained, it serves solely as an example application for integrating with Aarogya Setu OpenAPI.**

This is application is an integration with Aarogya Setu OpenAPI which allows you track your employees' COVID status and keep them safe. This code example is accompanied by this [blog post](https://aws.amazon.com/blogs/devops/integrating-with-aarogya-setu-open-api-on-aws-to-ensure-a-safe-workspace/).

## Instructions

We will be using AWS CDK to deploy our application stack. This will require you to install a few dependencies and tools, if you already have any of these installed please continue with the next step.

1. Install all the pre-requisites for [building and deploying cdk apps](https://cdkworkshop.com/15-prerequisites.html)
2. Install cdk in [python related prerequisites](https://cdkworkshop.com/15-prerequisites/600-python.html)
3. Register for a developer account at the [Asetu portal](https://openapi.aarogyasetu.gov.in/). You can only query status for the mobile number used to register the developer account.

For ease of demonstration and best experience this workshop assumes you have a user with Administrator access. You can configure more restrictive permissions for your user as required.

Note: The demo application is configured to deploy to `ap-south-1` region

Download or clone the repo and open a terminal inside it. Then follow the below steps to deploy your application. You can read the explanation of each step given below.

```Bash
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
cdk deploy asetuapi
# Fill the placeholders in `secrets.json`
python update-api-secret.py
cdk deploy asetuapifrontend
```

These commands perform operations equivalent to the following steps. You can paste the commands directly or make the changes yourself.

1. Clone or download this repository to directory and open it in terminal.
2. `python3 -m venv .env`  - Create a new virtual environnment to install dependencies. This creates a .env directory.
3. Activate the environment. If you're on Mac or Linux use `source .env/bin/activate`. If you're on windows use `.env\Scripts\activate.bat`
4. Install the required libraries using `pip install -r requirements.txt`
5. Deploy backend using `cdk deploy asetuapi`. This command will bundle up the dependencies and deploy the backend infrastructure for the application
6. The cdk app also creates a secret in the AWS Secrets Manager but it does not put the api secret values in it. Fill the placeholders in `secrets.json` with the values from your Aarogya Setu OpenAPI account and then run `python put-api-secret-value.py`. This will put values from `secrets.json` into AWS Secrets Manager.
7. Deploy the fronted using `cdk deploy asetuapifrontend`. It will package the frontend application for export and deploy the infrastructure. Open `asetuapifrontend.appurl` to access the web page.
8. Sign up as a new user and then log in. VOILA! You can now check COVID risk status and make your office safe for everyone.

### Cleaning up

You can remove both stacks using `cdk destroy asetuapi asetuapifrontend`. The S3 bucket can be deleted after you remove the static files stored in it, or you can use the following command, `aws s3 rb --force s3://<bucket-name>`. Finally you can delete the `CDKToolkit` stack or leave it as it is.
