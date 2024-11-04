import { getCookie } from './utils.js';
import { displayAvailableRooms, displayChatHistory, displayMessage } from './domUpdates.js';

import { showClosedRooms,showOpenRooms } from './tabSwitch.js';

const jwtToken = getCookie('jwt_token');
console.log(jwtToken)
if (!jwtToken) {
    console.error("JWT token is missing, cannot connect to Socket.IO server.");
}



export const socket = initSocket(getCookie('jwt_token'));

function initSocket(jwtToken) {
    const socket = io('http://localhost:5001/agent/agent_namespace', {
        transports: ['websocket', 'polling'],
        withCredentials: true,
        auth: { token: jwtToken }
    });

    socket.on('connect', () => console.log("Successfully connected"));
    socket.on('connect_ack', (data) => {
        console.log(data.message); // Should output: "Connected successfully"
    });
    socket.on('connect_error', error => console.error("Connection failed:", error));
    socket.on('disconnect', reason => console.warn("Disconnected:", reason));

    socket.on('available_rooms', roomData => {
        console.log("FE --- Received available rooms data:", roomData);
        displayAvailableRooms(roomData);
        showOpenRooms();

    });
    socket.on('chat_history', displayChatHistory);

    socket.on('message_from_user', data => {
        console.log("FE --- Received message from user:", data);
        displayMessage(data, 'user');
        showOpenRooms();
        
    });
    socket.on('message_from_business', data => displayMessage(data, 'business'));

    return socket;
}
