import { useState } from "react";

export default function InputGroup({
  placeholder,
  btnLabel,
  onSubmit,
  disabled,
}) {
  const [content, setContent] = useState("");

  return (
    <form
      className="input-group flex my-2 w-full"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(content);
        setContent("");
      }}
      style={{ height: "50px" }}
    >
      <input
        type="test"
        placeholder={placeholder}
        disabled={disabled}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className={`flex-1 border-2 border-gray-300 px-4 rounded
          focus:outline-none active:outline-none focus:border-blue-500
          active:border-blue-500 mr-2 h-full`}
      />
      <button
        type="submit"
        disabled={disabled}
        className={`w-auto h-full bg-blue-500 px-4 rounded text-white uppercase
          text-sm tracking-wide font-semibold hover:bg-blue-600 focus:outline-none
          active:outline-none focus:bg-blue-600 active:bg-blue-600`}
      >
        {btnLabel}
      </button>
    </form>
  );
}
