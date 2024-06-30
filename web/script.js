function sendMessage() {
  const userInput = document.getElementById('user-input');
  const message = userInput.value.trim();
  if (message === "") return;

  addMessageToChat("user", message);
  userInput.value = "";

  // Adiciona mensagem de "digitando..."
  const typingMessage = addMessageToChat("tech4ai", "• • •");
  
  fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message: message })
  })
    .then(response => response.json())
    .then(data => {
      // Remove a mensagem de "digitando..."
      typingMessage.remove();
      addMessageToChat("tech4ai", data.response);
    })
    .catch(error => {
      console.error('Error:', error);
      typingMessage.remove(); // Remove a mensagem de "digitando..." em caso de erro
      addMessageToChat("tech4ai", "Desculpe, não consegui processar sua informação...");
      fetch('/gerenciar_contexto.json', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify([])
      }).then(response => {
        if (response.ok) {
          console.log('Contexto reiniciado.');
        } else {
          console.error('Erro ao reiniciar contexto.');
        }
      }).catch(error => {
        console.error('Erro ao reiniciar contexto.', error);
      });
    });
}

function addMessageToChat(role, message) {
  const chatMessages = document.getElementById('chat-messages');
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', role);
  
  // Obtém o horário atual sem os segundos
  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  // Adiciona a mensagem e o horário
  messageElement.innerHTML = `
    <p>${message}</p>
    <span class="timestamp">${timestamp}</span>
  `;
  
  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return messageElement; // Retorna o elemento da mensagem
}

function displayWelcomeMessage() {
    const chatMessages = document.getElementById('chat-messages');
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const botMessage = `
        <div class="bot-message">
            <p>Olá ${nomeUsuario}, seja bem-vindo(a) à Tech4Humans!<br><br>
            Sou a Tech4.AI e estou aqui para te ajudar com sua adaptação na empresa.<br>
            Abaixo estão as funcionalidades que posso oferecer:<br>
            - Esclarecer dúvidas sobre a empresa;<br>
            - Agendar sua reunião de boas-vindas;<br>
            - Fornecer tutoriais das plataformas internas, como Github, Vscode, Jira e Discord.<br><br>
            Como posso ajudar você hoje?</p>
            <span class="timestamp">${timestamp}</span>
        </div>
    `;
    chatMessages.innerHTML += botMessage;
}

function signOut() {
  fetch('/logout', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  }).then(response => {
    if (response.ok) {
      console.log('Usuário desconectado.');
      window.location.href = '/';
    } else {
      console.error('Erro ao desconectar.');
    }
  }).catch(error => {
    console.error('Erro ao desconectar:', error);
  });
}

document.getElementById('logout-button').addEventListener('click', signOut);

function initGoogleAuth(clientId) {
  gapi.load('auth2', () => {
    gapi.auth2.init({
      client_id: clientId
    });
  });
}

function loadClientIdAndInitAuth() {
  fetch('../credentials.json') // Ajuste o caminho conforme necessário
    .then(response => response.json())
    .then(credentials => {
      const clientId = credentials.web.client_id;
      initGoogleAuth(clientId);
    })
    .catch(error => {
      console.error('Erro ao carregar o client_id:', error);
    });
}

window.onload = function() {
  displayWelcomeMessage();
  loadClientIdAndInitAuth();
};

document.getElementById('user-input').addEventListener('keypress', function(event) {
  if (event.key === 'Enter') {
    sendMessage();
  }
});