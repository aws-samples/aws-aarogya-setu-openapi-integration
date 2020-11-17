import { useState, useEffect } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import SweetAlert from "sweetalert-react";
import Amplify, { Auth } from "aws-amplify";
import awsconfig from "../aws-exports";
import API from "@aws-amplify/api";
import { withAuthenticator } from "@aws-amplify/ui-react";
import InputGroup from "../components/InputGroup.js";
import Table from "../components/Data.js";

import "sweetalert/dist/sweetalert.css";

Amplify.configure(awsconfig);

const dummyData = Array(10)
  .fill({ mobile_number: "+91 9812312300" })
  .map(({ mobile_number }) => {
    const y = Math.random() > 0.5;
    return {
      mobile_number,
      message: y ? "COVID positive" : "COVID negative",
      colour: y ? "#00ff00" : "#ff0000",
    };
  });

const SingleModalContent = ({ message, color, mobile_number }) => (
  <div>
    <div className={`text-center text-lg`}>{mobile_number}</div>
    <div className={`text-center my-5`} style={{ color }}>
      {message}
    </div>
  </div>
);

function Home() {
  const [message, setMessage] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [modalContent, setModalContent] = useState();
  const [modalVisible, setModalVisible] = useState(false);
  const [data, setData] = useState([]);

  useEffect(() => {
    API.configure();
  }, []);

  const handleSingleNumber = async (number) => {
    try {
      setLoading(true);
      setMessage(false);

      const user = await Auth.currentAuthenticatedUser();
      const token = user.signInUserSession.idToken.jwtToken;

      const res = await (
        await fetch(
          "https://suk3v9yzr4.execute-api.ap-south-1.amazonaws.com/prod/status",
          {
            method: "post",
            headers: { Authorization: token },
            body: JSON.stringify({ mobile_number: number }),
          }
        )
      ).json();

      setModalContent(() => (
        <SingleModalContent
          {...{
            mobile_number: res.mobile_number,
            colour: res.colour === "#FFFFFF" ? "#000000" : res.colour,
            message: res.message,
          }}
        />
      ));
      setModalVisible(true);

      setLoading(false);
    } catch (e) {
      console.error(e);
      setError("An error occurred");
      setLoading(false);
    }
  };

  const handleMultipleNumbers = async (raw) => {
    try {
      setLoading(true);
      setMessage(false);
      setError(false);
 
      const user = await Auth.currentAuthenticatedUser();
      const token = user.signInUserSession.idToken.jwtToken;

      const res = await (
        await fetch(
          "https://suk3v9yzr4.execute-api.ap-south-1.amazonaws.com/prod/bulk_status",
          {
            method: "post",
            headers: { Authorization: token },
            body: JSON.stringify({ numbers: raw }),
          }
        )
      ).json();

      console.log({ res });

      setMessage("Numbers sent to server. Press refresh to view statuses.");
      // setData([]);

      setLoading(false);
    } catch (e) {
      console.error(e);
      setError("An error occurred");
      // setData([]);
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    setMessage(false);
    setError(false);

    const user = await Auth.currentAuthenticatedUser();
    const token = user.signInUserSession.idToken.jwtToken;

    const res = await (
      await fetch(
        "https://suk3v9yzr4.execute-api.ap-south-1.amazonaws.com/prod/scan",
        {
          headers: { Authorization: token },
        }
      )
    ).json();

    if (Math.random() < 0.1) {
      setError("An error occurred");
      setData([]);
    } else {
      setData(res);
    }

    setLoading(false);
  };

  return (
    <div className="container w-full max-w-screen-md px-5 py-5 mx-auto">
      <InputGroup
        placeholder="Single mobile number"
        disabled={loading}
        onSubmit={handleSingleNumber}
        btnLabel="Check"
      />
      <InputGroup
        placeholder="Multiple comma-separated mobile numbers"
        disabled={loading}
        onSubmit={handleMultipleNumbers}
        btnLabel="Check"
      />

      {message && <div className={`text-center w-full text-sm`}>{message}</div>}
      {error && (
        <div className={`text-center w-full text-sm text-red-600`}>{error}</div>
      )}

      <SweetAlert
        show={modalVisible}
        title="Status"
        html
        text={renderToStaticMarkup(modalContent)}
        onConfirm={() => setModalVisible(false)}
      />

      <Table onRefresh={handleRefresh} data={data} />
    </div>
  );
}

export default withAuthenticator(Home);
