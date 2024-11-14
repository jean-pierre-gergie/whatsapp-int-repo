import { joinRoom, getCurrentRoom } from './roomManagement.js';
import { showOpenRooms, showClosedRooms } from './tabSwitch.js';
import { socket } from './socket.js';

function formatTimestamp(timestamp) {
    // Ensure the timestamp is in a valid ISO format by removing any microseconds
    const standardizedTimestamp = timestamp.split(".")[0] + "Z";
    const date = new Date(standardizedTimestamp); // Convert to Date object in UTC
    return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    }); // Local time format without specifying timeZone
}

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

    openRoomList.innerHTML = '';
    closedRoomList.innerHTML = '';

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

        const closeButton = document.createElement("span");
        closeButton.className = "close-button";
        closeButton.textContent = "✕";
        closeButton.onclick = (event) => {
            event.stopPropagation();
            closeRoom(room.room_id);
        };

        roomButton.appendChild(closeButton);
        roomButton.onclick = () => joinRoom(room.room_id);

        return roomButton;
    }

    roomData.openRooms.forEach(room => {
        const roomButton = createRoomButton(room);
        openRoomList.appendChild(roomButton);
    });

    roomData.closedRooms.forEach(room => {
        const roomButton = createRoomButton(room);
        closedRoomList.appendChild(roomButton);
    });
}

function closeRoom(roomId) {
    socket.emit('close_conversation', { room_id: roomId });
}

export function displayChatHistory(data) {
    console.log("Displaying chat history...");
    if (data.room !== getCurrentRoom()) {
        console.warn("Data room does not match current room:", data.room, "vs", getCurrentRoom());
        return;
    }

    const chatBody = document.getElementById("chat-body");
    chatBody.innerHTML = ''; // Clear chat body to ensure fresh render

    let lastDate = null; // To track the last date

    data.messages.forEach(message => {
        const formattedTime = formatTimestamp(message.timestamp); // Convert UTC to local time
        const messageDate = new Date(message.timestamp).toLocaleDateString(); // Get date part only

        // Check if this message's date is different from the last message's date
        if (messageDate !== lastDate) {
            // Create and insert a date card
            const dateCard = document.createElement("div");
            dateCard.classList.add("date-card"); // Style this in CSS
            dateCard.innerText = messageDate;
            chatBody.appendChild(dateCard);
            lastDate = messageDate; // Update the last date to current message's date
        }

        // Add the message itself
        addMessageToChatBody(message.body ?? message.message, message.sender, formattedTime);
    });

    console.log("Chat history displayed.");
}

export function displayMessage(data, sender) {
    if (data.room !== getCurrentRoom()) return console.warn("Message for different room:", data.room);
    const formattedTime = formatTimestamp(data.timestamp); // Convert UTC to local time
    addMessageToChatBody(data.message, sender, formattedTime);
}

function addMessageToChatBody(message, sender, timestamp) {
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

function scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
}
