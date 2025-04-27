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
  if (!url) {
    return;
  }
  const processForm = document.getElementById("url-form");
  processForm.classList.add("disabled")

  const loadMessage = document.getElementById("load-message");
  loadMessage.style.display = "block"
  loadMessage.classList.add('loading')

  document.getElementById("chat-container").style.display = "none";

  const baseUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
  const response = await fetch(`${baseUrl}/downloadWebsite`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({url: url})
  });

  const {task_id} = await response.json();

  checkProgress(task_id);
}

async function checkProgress(taskId) {
  const loadMessage = document.getElementById("load-message");
  const processForm = document.getElementById("url-form");
  try {

    const baseUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
    const response = await fetch(`${baseUrl}/progress/${taskId}`);
    const { status, text } = await response.json();

    if (status === "done") {
      loadMessage.innerText = text
      document.getElementById("chat-container").style.display = "grid";
      processForm.classList.remove("disabled")
      loadMessage.classList.remove('loading')
      document.getElementById("url-input").value = "";
    } else if (status === "error") {
      loadMessage.innerText = `❌ Error: ${text}`;
      loadMessage.classList.remove('loading')
      processForm.classList.remove("disabled")
      document.getElementById("chat-container").style.display = "grid";
    } else {
        // Guardar si estaba abajo antes de cambiar el texto
      const wasAtBottom = loadMessage.scrollTop + loadMessage.clientHeight >= loadMessage.scrollHeight - 5;

      // Actualizar el texto
      loadMessage.innerText = text;

      // Hacer scroll solo si estaba abajo antes
      if (wasAtBottom) {
        loadMessage.scrollTo({
          top: loadMessage.scrollHeight,
          behavior: "smooth"
        });
      }
      setTimeout(() => checkProgress(taskId), 500);
    }
  } catch (err) {
    console.error(err);
    document.getElementById("chat-container").style.display = "grid";
    loadMessage.innerText = "❌ Error checking progress.";
    loadMessage.classList.remove('loading');
    processForm.classList.remove("disabled")

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
    const baseUrl = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;

    const response = await fetch(`${baseUrl}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({query: input})
    });

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