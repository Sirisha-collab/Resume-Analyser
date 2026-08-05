import { useState } from "react";
import axios from "axios";
import { useLocation } from "react-router-dom";

export default function ResumeChat({ resumeId: propResumeId }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);

  const location = useLocation();
  const resumeId = propResumeId ?? location.state?.resumeId;

  const sendQuestion = async () => {
    if (!question.trim() || !resumeId) return;

    const userMessage = { role: "user", text: question };

    setMessages((prev) => [...prev, userMessage]);

    try {
      const res = await axios.post("http://127.0.0.1:5000/resume-chat", {
        resume_id: resumeId,
        question: question,
      });

      const aiMessage = { role: "ai", text: res.data.answer };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", text: "Error getting response" },
      ]);
    }

    setQuestion("");
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        padding: "20px",
      }}
    >
      <h2>Resume Chat</h2>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid #ccc",
          padding: "10px",
        }}
      >
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: "10px" }}>
            <b>{m.role === "user" ? "You" : "AI"}:</b>
            <div>{m.text}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", marginTop: "10px" }}>
        <input
          style={{ flex: 1 }}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about resume..."
        />

        <button onClick={sendQuestion}>Send</button>
      </div>
    </div>
  );
}