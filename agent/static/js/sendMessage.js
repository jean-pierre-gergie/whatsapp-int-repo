import { socket } from './socket.js';
import { getCurrentRoom } from './roomManagement.js';

function getBeirutTimeISO() {
    const beirutTime = new Date().toLocaleString("en-US", { timeZone: "Asia/Beirut" });
    const beirutDate = new Date(beirutTime);
    return beirutDate.toISOString();
}

export function sendMessage() {
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();
    const timestamp = new Date().toISOString(); // Use UTC ISO timestamp

    if (getCurrentRoom() && message) {
        socket.emit('message_from_business', {
            room: getCurrentRoom(),
            message,
            sender: 'business',
            timestamp // Send UTC timestamp
        });
        messageInput.value = '';
    } else {
        console.error("No room selected or message is empty");
    }
}