import { joinRoom, getCurrentRoom } from './roomManagement.js';
import { showOpenRooms,showClosedRooms } from './tabSwitch.js';
import { socket } from './socket.js';


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

    // Function to create a room button with unread messages count
    function createRoomButton(room) {
        const roomButton = document.createElement("button");
        roomButton.className = "room-button";
        roomButton.textContent = room.room_id;
    
        if (room.unread_count > 0) {
            const unreadBadge = document.createElement("span");
            unreadBadge.className = "unread-badge";
            unreadBadge.textContent = room.unread_count;
            roomButton.appendChild(unreadBadge);
        }
    
        // Create the close button as an "x"
        const closeButton = document.createElement("span");
        closeButton.className = "close-button";
        closeButton.textContent = "✕";  // Use a small "x" symbol
        closeButton.onclick = (event) => {
            event.stopPropagation();
            closeRoom(room.room_id);
        };
    
        // Append the close button to the room button
        roomButton.appendChild(closeButton);
        roomButton.onclick = () => joinRoom(room.room_id);
    
        return roomButton;
    }

    // Populate open rooms
    roomData.openRooms.forEach(room => {
        const roomButton = createRoomButton(room);
        openRoomList.appendChild(roomButton);
    });

    // Populate closed rooms
    roomData.closedRooms.forEach(room => {
        const roomButton = createRoomButton(room);
        closedRoomList.appendChild(roomButton);
    });
}

// Function to close the room by calling an API or emitting an event
function closeRoom(roomId) {
    // Emit an event to the server (if using Socket.IO)
    socket.emit('close_conversation', { room_id: roomId });

  
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