// static/js/messageDisplay.js

function displayChatHistory(data) {
    if (data.room !== currentRoom) return;
    const chatBody = document.getElementById("chat-body");
    data.messages.forEach(message => addMessageToChatBody(message.body, message.sender));
}

function displayMessage(data, sender) {
    if (data.room !== currentRoom) {
        return console.warn("Message for different room:", data.room);
    }
    addMessageToChatBody(data.message.body, sender);
}

function addMessageToChatBody(message, sender) {
    const chatBody = document.getElementById("chat-body");
    const messageElement = document.createElement("div");
    messageElement.className = `message ${sender}`;
    messageElement.textContent = message;
    chatBody.appendChild(messageElement);
    scrollToBottom(chatBody);
}

export { displayChatHistory, displayMessage, addMessageToChatBody };
