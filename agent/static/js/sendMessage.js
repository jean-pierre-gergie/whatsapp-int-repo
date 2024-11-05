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
    const timestamp = getBeirutTimeISO(); // Generate Beirut time in ISO format

    if (getCurrentRoom() && message) {
        socket.emit('message_from_business', {
            room: getCurrentRoom(),
            message,
            sender: 'business',
            timestamp // Include Beirut timestamp in the emitted data
        });
        messageInput.value = '';
    } else {
        console.error("No room selected or message is empty");
    }
}