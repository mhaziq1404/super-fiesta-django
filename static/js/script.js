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
