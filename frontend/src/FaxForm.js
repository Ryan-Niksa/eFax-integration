import React, { useState } from "react";

function FaxForm() {
  const [toNumber, setToNumber] = useState("");
  const [fromNumber, setFromNumber] = useState("");
  const [coverLetter, setCoverLetter] = useState("");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("to_number", toNumber);
    formData.append("from_number", fromNumber);
    formData.append("cover_letter", coverLetter);
    if (file) formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/send-fax/", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setStatus(`Fax sent! ID: ${data.fax_id || JSON.stringify(data)}`);
      } else {
        setStatus("Error: " + (data.detail || JSON.stringify(data)));
      }
    } catch (err) {
      setStatus("Request failed: " + err.message);
    }
  };

  return (
    <div className="max-w-lg mx-auto mt-10 p-6 bg-white rounded-2xl shadow-lg">
      <h1 className="text-2xl font-bold mb-6">📠 Send a Fax</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          placeholder="To Number"
          value={toNumber}
          onChange={(e) => setToNumber(e.target.value)}
          className="w-full p-2 border rounded"
          required
        />
        <input
          type="text"
          placeholder="From Number"
          value={fromNumber}
          onChange={(e) => setFromNumber(e.target.value)}
          className="w-full p-2 border rounded"
        />
        <textarea
          placeholder="Type your cover letter..."
          value={coverLetter}
          onChange={(e) => setCoverLetter(e.target.value)}
          className="w-full p-2 border rounded h-32"
        />
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files[0])}
          className="w-full"
        />
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700"
        >
          Send Fax
        </button>
      </form>
      {status && <p className="mt-4 text-sm">{status}</p>}
    </div>
  );
}

export default FaxForm;
