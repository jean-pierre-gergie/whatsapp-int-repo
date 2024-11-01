import { socket } from './socket.js';
import { getCurrentRoom } from './roomManagement.js';

export function sendMessage() {
    const messageInput = document.getElementById("message-input");
    const message = messageInput.value.trim();
    if (getCurrentRoom() && message) {
        socket.emit('message_from_business', { room: getCurrentRoom(), message, sender: 'business' });
        messageInput.value = '';
    } else {
        console.error("No room selected or message is empty");
    }
}