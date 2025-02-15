document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    
    feather.replace();

    function appendMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'ai-message'} mb-3`;
        
        const messageContent = document.createElement('div');
        messageContent.className = `p-3 rounded ${isUser ? 'bg-primary text-white ms-auto' : 'bg-secondary'}`
        messageContent.style.maxWidth = '75%';
        messageContent.textContent = message;
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;

        // Add user message
        appendMessage(message, true);
        messageInput.value = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            // Add AI response
            appendMessage(data.response);
        } catch (error) {
            console.error('Error:', error);
            appendMessage('Sorry, I encountered an error. Please try again.');
        }
    });
});
