# ASETUAPI

This is application is an integration with Aarogya Setu OpenAPI which allows you track your employees' COVID status and keep them safe.

## Instructions

We will be using AWS CDK to deploy our application stack. This will require you to install a few dependencies and tools, if you already have any of these installed please continue with the next step.

1. Install aws cli - https://cdkworkshop.com/15-prerequisites/100-awscli.html
2. Create an aws account and user that you will use to deploy the application - https://cdkworkshop.com/15-prerequisites/100-awscli.html
3. Install node js, we'll need this to install aws cdk - https://cdkworkshop.com/15-prerequisites/300-nodejs.html
4. Install aws-cdk toolkit - https://cdkworkshop.com/15-prerequisites/500-toolkit.html
5. Install python - https://cdkworkshop.com/15-prerequisites/600-python.html

The above steps install all the tools needed to work with AWS CDK projects. Open a terminal and follow the below steps to deploy your application.

1. Clone or Download this repository to directory and `cd` into it. - `cd asetuapi`
2. We'll have to install dependencies and build the frontend application in the client directory. `npm install --prefix client && npm run build --prefix client`
3. Run `cdk ls` and you should see two stacks namely `asetuapi` for the backend and `asetuapifrontend` for the frontend
4. Create a new virtual environnment to install stack related libraries. This creates a .env directory. `python3 -m venv .env`
5. Activate the environment. If you're on Mac or Linux use `source .env/bin/activate`. If you're on windows use `.env\Scripts\activate.bat`
6. Install the required libraries using `pip install -r requirements.txt`
7. Bootstrap resources in your account so that cdk can deploy the application. `cdk bootstrap`
8. Deploy backend using `cdk deploy asetuapi -y`. When deployment completes it will output the values of some resources we'll need these in the next step.
9. Open the `client/src/aws-exports.js` file. Copy the previous values to their respective locations. For e.g. the value for `asetuapi.apiname` should be replace the placeholder for `<apiname>`. Save and close the file.
10. Build the frontend appliaction again using `npm install --prefix client && npm run build --prefix client`
11. Deploy the fronted using `cdk deploy asetuapifrontend -y`. Note down the urls you receive, `asetuapifrontend.appurl` value is for the webpage where you can submit requests and the other is for viewing the user status table.
12. VOILA! You can now ensure your employees are safe and sound.

## CI/CD with CDK

1. https://docs.aws.amazon.com/cdk/latest/guide/cdk_pipeline.html
2. `export CDK_NEW_BOOTSTRAP=1`
3. `npx cdk bootstrap`
