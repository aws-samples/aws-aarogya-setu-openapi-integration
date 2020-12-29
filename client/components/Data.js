export default function Table({ onRefresh, data }) {
  return (
    <div className="data-table my-10 w-full">
      <button
        onClick={onRefresh}
        style={{ height: "60px" }}
        className={`w-full bg-blue-500 px-4 rounded text-white uppercase
          text-sm tracking-wide font-semibold hover:bg-blue-600 focus:outline-none
          active:outline-none focus:bg-blue-600 active:bg-blue-600`}
      >
        Refresh
      </button>

      <table
        className="my-5 border-3 border-gray-500 h-auto w-full"
        style={{ borderCollapse: "collapse" }}
      >
        <tbody>
          <tr className="bg-blue-500 color-white rounded-t border-none h-auto">
            <th
              className={`text-white rounded-tl border-none py-3 uppercase
              font-semibold tracking-wide text-sm`}
            >
              Phone
            </th>
            <th
              className={`text-white rounded-tr border-none py-3 uppercase
              font-semibold tracking-wide text-sm`}
            >
              Status
            </th>
          </tr>
          {data.map(({ mobile_number, message, colour }, i) => (
            <tr key={i}>
              <td
                className={`px-3 py-4 text-center ${
                  i % 2 === 0 ? "bg-blue-100" : "bg-gray-100"
                }`}
              >
                {mobile_number}
              </td>
              <td
                className={`px-3 py-4 text-center`}
                style={{ background: `${colour}20` }}
              >
                {message}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
