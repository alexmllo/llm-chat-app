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
  const url_form = document.getElementById("url-form");
  const spinner = document.getElementById("spinner");

  if (!url) return;

  url_form.style.display = "none";

  // Mostrar mensaje con spinner
  spinner.style.display = "block";

  // Forzar repintado para mostrar spinner antes del fetch
  await new Promise(resolve => setTimeout(resolve, 50));

  try {
    const response = await fetch("http://localhost:8080/downloadWebsite", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url: url })
    });

    const data = await response.text(); // <-- tu backend devuelve texto plano

    if (response.ok) {
      spinner.style.display = "none";
      document.getElementById("chat-container").style.display = "block";
    } else {
      agentMessage.innerHTML = "❌ Error al procesar la URL: " + data;
    }
  } catch (error) {
    agentMessage.innerHTML = "❌ Error al conectar con el servidor.";
    console.error(error);
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
  agentMessage.textContent = "Pensando...";
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

    agentMessage.textContent = `${data}`;
  } catch (error) {
    agentMessage.textContent = "Error - No se pudo conectar con el servidor.";
    console.error(error);
  }

  chatBox.scrollTop = chatBox.scrollHeight;
}