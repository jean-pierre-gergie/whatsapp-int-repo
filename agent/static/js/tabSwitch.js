export function showOpenRooms() {
    document.getElementById('open-room-list').style.display = 'block';
    document.getElementById('closed-room-list').style.display = 'none';
    document.querySelector('.tabs button:nth-child(1)').classList.add('selected');
    document.querySelector('.tabs button:nth-child(2)').classList.remove('selected');
}

export function showClosedRooms() {
    document.getElementById('open-room-list').style.display = 'none';
    document.getElementById('closed-room-list').style.display = 'block';
    document.querySelector('.tabs button:nth-child(1)').classList.remove('selected');
    document.querySelector('.tabs button:nth-child(2)').classList.add('selected');
}