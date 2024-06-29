function sendMessage() {
  const userInput = document.getElementById('user-input');
  const message = userInput.value.trim();
  if (message === "") return;

  addMessageToChat("user", message);
  userInput.value = "";

  fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message: message })
  })
    .then(response => response.json())
    .then(data => {
      addMessageToChat("tech4ai", data.response);
    })
    .catch(error => {
      console.error('Error:', error);
    });
}

function addMessageToChat(role, message) {
  const chatMessages = document.getElementById('chat-messages');
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', role);
  messageElement.innerHTML = message; // Usar innerHTML para permitir formatação HTML
  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function displayWelcomeMessage() {
    const chatMessages = document.getElementById('chat-messages');
    const botMessage = `
        <div class="bot-message">
            <p>Olá! Seja bem-vindo(a) à Tech4Humans!<br><br>
            Sou a Tech4.AI e estou aqui para te ajudar com sua adaptação na empresa.<br>
            Abaixo estão as funcionalidades que posso oferecer:<br>
            - Esclarecer dúvidas sobre a empresa;<br>
            - Agendar sua reunião de boas-vindas;<br>
            - Fornecer tutoriais das plataformas internas, como Github, Vscode, Jira e Discord.<br><br>
            Como posso ajudar você hoje?</p>
        </div>
    `;
    chatMessages.innerHTML += botMessage;
}
window.onload = displayWelcomeMessage;

document.getElementById('user-input').addEventListener('keypress', function(event) {
  if (event.key === 'Enter') {
    sendMessage();
  }
});
