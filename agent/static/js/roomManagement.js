import { socket } from './socket.js';
import { updateRoomName, clearChatBody } from './domUpdates.js';

let currentRoom = null;

export function joinRoom(room) {
    console.log("Joining room:", room);
    currentRoom = room;
    socket.emit('join_room', { room });
    updateRoomName(room);
    clearChatBody();
}

export function getCurrentRoom() {
    return currentRoom;
}
