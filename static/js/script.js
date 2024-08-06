function scrollToBottom(time=0) {
    setTimeout(function() {
        const container = document.getElementById('chat_container');
        container.scrollTop = container.scrollHeight;
    }, time);
}
scrollToBottom()
