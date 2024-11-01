import { sendMessage } from './sendMessage.js';
import { showOpenRooms, showClosedRooms } from './tabSwitch.js';

document.getElementById("message-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        sendMessage();
        event.preventDefault();
    }
});

document.querySelector(".chat-footer button").onclick = sendMessage;

document.querySelector(".tabs button:nth-child(1)").onclick = showOpenRooms;
document.querySelector(".tabs button:nth-child(2)").onclick = showClosedRooms;