export const searchDocumentsStream = async (
  query,
  onMessage,
  onError,
  onComplete,
) => {
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");

      // Keep the last partial chunk in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.substring(6);
          try {
            const data = JSON.parse(dataStr);
            if (data.type === "done") {
              onComplete();
              return;
            }
            onMessage(data);
          } catch (e) {
            console.error("Error parsing JSON chunk:", e, dataStr);
          }
        }
      }
    }
    onComplete();
  } catch (error) {
    onError(error);
  }
};
