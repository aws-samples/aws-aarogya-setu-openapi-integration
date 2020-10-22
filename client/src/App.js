import React from "react";
import logo from "./logo.svg";
import "./App.css";
import Amplify, { Auth } from "aws-amplify";
import awsconfig from "./aws-exports";
import API, { graphqlOperation } from "@aws-amplify/api";
import { withAuthenticator, AmplifySignOut } from "@aws-amplify/ui-react";
import "bootstrap/dist/css/bootstrap.min.css";
import Button from "react-bootstrap/Button";
import Table from "react-bootstrap/Table";

Amplify.configure(awsconfig);

class App extends React.Component {
  // define some state to hold the data returned from the API

  constructor(props) {
    super(props);
    this.getStatus = this.getStatus.bind(this);

    API.configure();
  }

  state = {
    status: "",
    bulk_status: "",
    bulk_output: "",
    stat_output: "",
  };

  handleChangeStatus(e) {
    this.setState({ status: e.target.value });
  }

  handleChangeBulkStatus(e) {
    this.setState({ bulk_status: e.target.value });
  }

  async getBulkStatus() {
    console.log("pressed status");
    console.log(this.state.bulk_status);

    console.log("pressed status");

    const apiName = awsconfig.aws_cloud_logic_custom[0].name; // replace this with your api name.
    const path = "/bulk_status"; //replace this with the path you have configured on your API
    const user = await Auth.currentAuthenticatedUser()
    const token = user.signInUserSession.idToken.jwtToken;
    const myInit = {
      response: true,
      headers: {
        Authorization: token
      },
      body: { numbers: this.state.bulk_status }, // replace this with attributes you need
    };

    API.post(apiName, path, myInit)
      .then((response) => {
        console.log("checking now");
        console.log("recieved response -> " + response.data);
        this.setState({ bulk_output: response.data });
      })
      .catch((error) => {
        console.log(error);
      });
  }

  async getStatus() {
    console.log("pressed status");
    console.log(this.state.status);

    console.log("pressed status");

    const apiName = awsconfig.aws_cloud_logic_custom[0].name; // replace this with your api name.
    const path = "/status"; //replace this with the path you have configured on your API
    const user = await Auth.currentAuthenticatedUser()
    const token = user.signInUserSession.idToken.jwtToken;
    const myInit = {
      response: true,
      headers: {
        Authorization: token
      },
      body: { mobile_number: this.state.status }, // replace this with attributes you need
    };

    API.post(apiName, path, myInit)
      .then((response) => {
        console.log("checking now");
        console.log("recieved response -> " + response.data);
        this.setState({ stat_output: response.data });
      })
      .catch((error) => {
        console.log(error);
      });
  }

  render() {
    return (
      <div id="1" style={{ display: "flex", justifyContent: "center" }}>
        <Table striped bordered hover>
          <thead>
            <tr>
              <td>
                <div>
                  <input
                    type="text"
                    onChange={this.handleChangeStatus.bind(this)}
                  />
                  <Button
                    data-item="add-item"
                    variant="primary"
                    onClick={this.getStatus.bind(this)}
                  >
                    Get Status
                  </Button>
                </div>
              </td>
              <td>
                <div>
                  <input
                    type="text"
                    onChange={this.handleChangeBulkStatus.bind(this)}
                  />
                  <Button
                    data-item="add-item"
                    variant="primary"
                    onClick={this.getBulkStatus.bind(this)}
                  >
                    Get Bulk Status
                  </Button>
                </div>
              </td>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>STATUS : {this.state.stat_output}</td>
              <td>BULK STATUS : {this.state.bulk_output}</td>
            </tr>
          </tbody>
        </Table>
      </div>
    );
  }
}

//export default App;
export default withAuthenticator(App);
