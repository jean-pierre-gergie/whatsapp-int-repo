// static/js/messageDisplay.js

function formatTimestamp(utcTimestamp) {
    const date = new Date(utcTimestamp); // Convert UTC to Date object
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); // Local time format
}

function displayChatHistory(data) {
    console.log("DisplayChatHistory...")
    const browser = new Date();
    console.log("Local Time:", browser.toLocaleString());
    if (data.room !== currentRoom) return;
    const chatBody = document.getElementById("chat-body");
    data.messages.forEach(message => {
        const formattedTime = formatTimestamp(message.timestamp); // Convert UTC to local
        addMessageToChatBody(message.body, message.sender, formattedTime);
    });
}

function displayMessage(data, sender) {
    console.log("DisplayMessage...")
    const browser = new Date();
    console.log("Local Time:", browser.toLocaleString());
    if (data.room !== currentRoom) {
        return console.warn("Message for different room:", data.room);
    }
    const formattedTime = formatTimestamp(data.timestamp); // Convert UTC to local
    addMessageToChatBody(data.message.body, sender, formattedTime);
}

function addMessageToChatBody(message, sender, timestamp) {
    console.log("adding message to chat body...")
    const browser = new Date();
    console.log("Local Time:", browser.toLocaleString());
    const chatBody = document.getElementById("chat-body");

    const messageElement = document.createElement("div");
    messageElement.className = `message ${sender}`;

    const messageBody = document.createElement("p");
    messageBody.className = "message-body";
    messageBody.textContent = message;

    const timestampElement = document.createElement("span");
    timestampElement.className = "timestamp";
    timestampElement.textContent = timestamp; // Display formatted timestamp

    messageElement.appendChild(messageBody);
    messageElement.appendChild(timestampElement);
    chatBody.appendChild(messageElement);

    scrollToBottom(chatBody);
}

export { displayChatHistory, displayMessage, addMessageToChatBody };
