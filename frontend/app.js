document.getElementById("user-input").addEventListener("keypress", function (e) {
  if (e.key === "Enter") {
    sendQuery();
  }
});

document.getElementById("url-input").addEventListener("keypress", function (e) {
  if (e.key === "Enter") {
    processUrl();
  }
});

async function processUrl() {
  const url = document.getElementById("url-input").value.trim();
  const loadMessage = document.getElementById("load-message");

  if (!url) return;

  loadMessage.style.display = "block"
  loadMessage.classList.add('loading')

  document.getElementById("chat-container").style.display = "none";
      const response = await fetch("http://localhost:8080/downloadWebsite", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: url })
    });

    const { task_id } = await response.json();

    checkProgress(task_id);

}

async function checkProgress(taskId) {
  const loadMessage = document.getElementById("load-message");

  try {
    const response = await fetch(`http://localhost:8080/progress/${taskId}`);
    const { status, text } = await response.json();

    if (status === "done") {
      loadMessage.innerText = text
      document.getElementById("chat-container").style.display = "grid";
      loadMessage.classList.remove('loading')

    } else if (status === "error") {
      loadMessage.innerText = `❌ Error: ${text}`;
      loadMessage.classList.remove('loading')
      document.getElementById("chat-container").style.display = "grid";
    } else {
      // Seguir comprobando cada 2 segundos
      loadMessage.innerText = text
      loadMessage.scrollTo({
          top: loadMessage.scrollHeight,
          behavior: "smooth"
        });
      setTimeout(() => checkProgress(taskId), 200);
    }
  } catch (err) {
    console.error(err);
    document.getElementById("chat-container").style.display = "grid";
    loadMessage.innerText = "❌ Error checking progress.";
    loadMessage.classList.remove('loading')

  }
}

async function sendQuery() {
  const inputEl = document.getElementById("user-input");
  const input = inputEl.value.trim();
  const chatBox = document.getElementById("chat-box");

  if (!input) return;

  // Mostrar mensaje del usuario
  const userMessage = document.createElement("div");
  userMessage.className = "chat-message user";
  userMessage.textContent = `${input}`;
  chatBox.appendChild(userMessage);

  // Mensaje de espera de la IA
  const agentMessage = document.createElement("div");
  agentMessage.className = "chat-message agent";
  agentMessage.textContent = "Thinking...";
  chatBox.appendChild(agentMessage);

  chatBox.scrollTop = chatBox.scrollHeight;
  inputEl.value = "";

  try {
    const response = await fetch("http://localhost:5050/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ query: input })
    });
    // const url = `${window.location.origin}/query?query=${encodeURIComponent(input)}`;
    // const response = await fetch(url);
    const data = await response.text();

    const formattedData = data
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    agentMessage.innerHTML = `${formattedData}`;
  } catch (error) {
    agentMessage.textContent = "Error - No se pudo conectar con el servidor.";
    console.error(error);
  }

  chatBox.scrollTop = chatBox.scrollHeight;
}