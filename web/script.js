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

document.getElementById('user-input').addEventListener('keydown', function(event) {
  if (event.key === 'Enter') {
    sendMessage();
  }
});
