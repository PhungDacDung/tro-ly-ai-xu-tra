// src/App.js
import React, { useState, useEffect, useRef } from 'react';
import '../App.css';

const ChatApp = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // Tự động cuộn xuống cuối khi có tin nhắn mới
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Thêm câu hỏi vào danh sách tin nhắn
    const newMessage = { text: input, sender: 'user' };
    setMessages((prev) => [...prev, newMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:5000/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: newMessage.text }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessages((prev) => [
          ...prev,
          { text: data.answer, sender: 'bot' },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { text: `Lỗi: ${data.error || 'Không thể xử lý câu hỏi'}`, sender: 'bot' },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { text: 'Lỗi: Không thể kết nối đến server', sender: 'bot' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-app">
      <header className="chat-header">
        <h1>Trợ lý AI xứ trà</h1>
        <p>Hỏi đáp về đặc sản trà Thái Nguyên</p>
      </header>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              Chào bạn! Bạn muốn biết thông tin gì về đặc sản trà Thái Nguyên.
            </div>
          )}
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${msg.sender === 'user' ? 'user' : 'bot'}`}
            >
              <div className="message-content">{msg.text}</div>
            </div>
          ))}
          {loading && (
            <div className="message bot">
              <div className="message-content typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleSend} className="chat-input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập câu hỏi của bạn..."
            className="chat-input"
            disabled={loading}
          />
          <button type="submit" className="send-btn" disabled={loading}>
            Gửi
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatApp;