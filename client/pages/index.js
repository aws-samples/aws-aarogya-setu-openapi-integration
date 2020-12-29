import { useState, useEffect } from "react";
import { ToastProvider, useToasts } from "react-toast-notifications";
import Amplify, { Auth } from "aws-amplify";
import awsconfig from "../aws-exports";
import API from "@aws-amplify/api";
import { withAuthenticator } from "@aws-amplify/ui-react";
import InputGroup from "../components/InputGroup.js";
import Table from "../components/Data.js";

Amplify.configure(awsconfig);

function Home() {
  const [message, setMessage] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const { addToast } = useToasts();

  const api_endpoint = awsconfig.aws_api_endpoint;
  const single_number_url = api_endpoint + "status";
  const bulk_number_url = api_endpoint + "bulk_status";
  const scan_url = api_endpoint + "scan";

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
        await fetch(single_number_url, {
          method: "post",
          headers: { Authorization: token },
          body: JSON.stringify({ mobile_number: number }),
        })
      ).json();

      addToast(res.message, {
        appearance: "info",
      });

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
        await fetch(bulk_number_url, {
          method: "post",
          headers: { Authorization: token },
          body: JSON.stringify({ numbers: raw }),
        })
      ).json();

      console.log({ res });

      setMessage("Numbers sent to server. Press refresh to view statuses.");
      setData([]);

      setLoading(false);
    } catch (e) {
      console.error(e);
      setError("An error occurred");
      setData([]);
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
      await fetch(scan_url, {
        headers: { Authorization: token },
      })
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

      <Table onRefresh={handleRefresh} data={data} />
    </div>
  );
}

function HomeExport() {
  return (
    <ToastProvider>
      <Home />
    </ToastProvider>
  );
}

export default withAuthenticator(HomeExport);
