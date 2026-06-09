function DocumentViewer({ document, onClose }) {
  return (
    <div className="doc-viewer">
      <span
        className="close-btn"
        onClick={onClose}
      >
        ✕
      </span>

      <h2>{document.title}</h2>

      <p>
        <strong>Source:</strong>{" "}
        {document.source}
      </p>

      <p>
        <strong>Path:</strong>{" "}
        {document.path}
      </p>

      {document.url && (
        <p>
          <strong>GitHub:</strong>{" "}
          <a
            href={document.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open Document
          </a>
        </p>
      )}

      <hr />

      <p>{document.content}</p>
    </div>
  );
}

export default DocumentViewer;