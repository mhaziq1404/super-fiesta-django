function scrollToBottom(time=0) {
    setTimeout(function() {
        const container = document.getElementById('chat_container');
        container.scrollTop = container.scrollHeight;
    }, time);
}
scrollToBottom()

function markAsRead(notificationId) {
    fetch(`/notifications/mark_as_read/${notificationId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({ 'is_read': true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Optionally remove or update the notification in the UI
            location.reload();
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const chatbox = document.getElementById('chatbox');
    const toggleButton = document.getElementById('chatbox-toggle');

    toggleButton.addEventListener('click', function() {
        if (chatbox.classList.contains('hidden')) {
            chatbox.classList.remove('hidden');
            chatbox.classList.add('show');
        } else {
            chatbox.classList.remove('show');
            chatbox.classList.add('hidden');
        }
    });
});
