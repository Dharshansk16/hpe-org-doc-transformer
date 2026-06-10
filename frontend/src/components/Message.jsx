import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function Message({ message, onCiteClick }) {
  const [showSources, setShowSources] = useState(false);
  const sources = message.sources || [];

  const renderContent = (text) => {
    if (!text) return null;
    if (message.role === "user") return text;

    const processedText = text.replace(/\[(\d+)\](?!\()/g, "[$1](#cite-$1)");

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children, ...props }) => {
            if (href && href.startsWith("#cite-")) {
              const index = parseInt(href.replace("#cite-", ""), 10) - 1;
              const source = message.sources && message.sources[index];
              if (source && onCiteClick) {
                return (
                  <span
                    onClick={(e) => {
                      e.preventDefault();
                      onCiteClick(source);
                    }}
                    style={{
                      color: "#007bff",
                      cursor: "pointer",
                      textDecoration: "underline",
                      fontWeight: "bold",
                    }}
                    title={`View Source ${index + 1}`}
                  >
                    {children}
                  </span>
                );
              }
            }
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {processedText}
      </ReactMarkdown>
    );
  };

  return (
    <div
      className={`message ${message.role === "user" ? "user" : "assistant"}`}
      style={{ lineHeight: "1.5", overflowX: "auto" }}
    >
      {/* MESSAGE CONTENT */}
      {message.role === "user" ? (
        <div style={{ whiteSpace: "pre-wrap" }}>{message.content}</div>
      ) : (
        renderContent(message.content)
      )}

      {/* SOURCES TOGGLE BUTTON */}
      {message.role === "assistant" && sources.length > 0 && (
        <button
          onClick={() => setShowSources(!showSources)}
          style={{
            marginTop: "6px",
            fontSize: "12px",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: "#666",
          }}
        >
          {showSources ? "Hide sources ▲" : `Sources (${sources.length}) ▼`}
        </button>
      )}

      {/* SOURCES PANEL */}
      {showSources && sources.length > 0 && (
        <div
          style={{
            marginTop: "10px",
            paddingLeft: "10px",
            borderLeft: "3px solid #ddd",
          }}
        >
          {sources.map((s, index) => (
            <div
              key={index}
              onClick={() => onCiteClick?.(s)}
              style={{
                marginBottom: "10px",
                padding: "8px",
                background: "#f9f9f9",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              <div style={{ fontWeight: "600" }}>
                [{index + 1}] {s.title || s.doc_id}
              </div>

              {s.source && (
                <div style={{ fontSize: "12px", color: "#555" }}>
                  {s.source}
                </div>
              )}

              {s.url && (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  style={{ fontSize: "12px", color: "#007bff" }}
                >
                  Open source ↗
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Message;
