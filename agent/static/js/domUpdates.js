import { joinRoom, getCurrentRoom } from './roomManagement.js';
import { showOpenRooms,showClosedRooms } from './tabSwitch.js';

export function updateRoomName(room) {
    document.getElementById("room-name").textContent = `Room: ${room}`;
}

export function clearChatBody() {
    document.getElementById("chat-body").innerHTML = '';
}

export function displayAvailableRooms(roomData) {
    
    const openRoomList = document.getElementById("open-room-list");
    const closedRoomList = document.getElementById("closed-room-list");
    if (!openRoomList || !closedRoomList) {
        return console.error("Room lists not found");
    }

    // Clear previous room data
    openRoomList.innerHTML = '';
    closedRoomList.innerHTML = '';

    // Populate open rooms
    roomData.openRooms.forEach(room => {
        const roomButton = document.createElement("button");
        roomButton.className = "room-button";
        roomButton.textContent = room;
        roomButton.onclick = () => joinRoom(room);
        openRoomList.appendChild(roomButton);
    });

    // Populate closed rooms
    roomData.closedRooms.forEach(room => {
        const roomButton = document.createElement("button");
        roomButton.className = "room-button";
        roomButton.textContent = room;
        roomButton.onclick = () => joinRoom(room);
        closedRoomList.appendChild(roomButton);
    });

    showOpenRooms();
}

// export function displayChatHistory(data) {
//     if (data.room !== getCurrentRoom()) return;
//     const chatBody = document.getElementById("chat-body");
//     data.messages.forEach(message => addMessageToChatBody(message.body ?? message.message, message.sender));
// }
export function displayChatHistory(data) {
    if (data.room !== getCurrentRoom()) return;
    const chatBody = document.getElementById("chat-body");
    data.messages.forEach(message => addMessageToChatBody(message.body , message.sender));
}

// export function displayMessage(data, sender) {
//     if (data.room !== getCurrentRoom()) return console.warn("Message for different room:", data.room);
//     addMessageToChatBody(data.body ?? data.message, sender);
// }

export function displayMessage(data, sender) {
    console.log("updating message coming form:", sender)
    if (data.room !== getCurrentRoom()) return console.warn("Message for different room:", data.room);
    addMessageToChatBody(data.message, sender);
}

function addMessageToChatBody(message, sender) {
    const chatBody = document.getElementById("chat-body");
    const messageElement = document.createElement("div");
    messageElement.className = `message ${sender}`;
    messageElement.textContent = message;
    chatBody.appendChild(messageElement);
    scrollToBottom(chatBody);
}

function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}