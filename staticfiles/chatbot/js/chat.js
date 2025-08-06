// PoBot Chatbot JavaScript

$(document).ready(function() {
    // Check if this is a new browser session (cleared on browser refresh/close)
    let startNewSession = !sessionStorage.getItem('chatSessionActive');
    
    // Mark session as active
    if (startNewSession) {
        sessionStorage.setItem('chatSessionActive', 'true');
    }
    
    // Add initial bot message
    if ($('#messages').children().length === 0) {
        addBotMessage("Hello! I am PoBot, your legal AI assistant. Which language would you like to continue the conversation with?");
    }
    
    // Handle form submission
    $('#chat-form').submit(function(e) {
        e.preventDefault();
        const userInput = $('#user-input').val().trim();
        if (userInput) {
            // Add user message to chat
            addUserMessage(userInput);
            
            // Clear input field
            $('#user-input').val('');
            
            // Show typing indicator
            showTypingIndicator();
            
            // Send message to server
            $.ajax({
                url: chatMessageUrl,
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ 
                    message: userInput,
                    new_session: startNewSession
                }),
                success: function(response) {
                    // Hide typing indicator
                    hideTypingIndicator();
                    
                    // Add bot response to chat
                    addBotMessage(response.message);
                    
                    // After first message, ensure subsequent messages don't create new sessions
                    startNewSession = false;
                    
                    // If conversation is complete, redirect to dashboard
                    if (response.complete) {
                        setTimeout(function() {
                            addBotMessage("Redirecting to dashboard...");
                            setTimeout(function() {
                                window.location.href = dashboardUrl;
                            }, 2000);
                        }, 1000);
                    }
                },
                error: function() {
                    // Hide typing indicator
                    hideTypingIndicator();
                    
                    addBotMessage("Sorry, there was an error processing your request. Please try again.");
                }
            });
        }
    });
    
    // Function to add user message to chat
    function addUserMessage(message) {
        const currentTime = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const messageDiv = $(`
            <div class="message user-message">
                <div class="message-header">
                    <div class="message-sender">
                        <i class="fas fa-user message-icon"></i>
                        <span class="sender-name">You</span>
                    </div>
                    <span class="message-time">${currentTime}</span>
                </div>
                <div class="message-content">${message}</div>
            </div>
        `);
        $('#messages').append(messageDiv);
        scrollToBottom();
    }
    
    // Function to add bot message to chat
    function addBotMessage(message) {
        const currentTime = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const messageDiv = $(`
            <div class="message bot-message">
                <div class="message-header">
                    <div class="message-sender">
                        <i class="fas fa-robot message-icon"></i>
                        <span class="sender-name">PoBot</span>
                    </div>
                    <span class="message-time">${currentTime}</span>
                </div>
                <div class="message-content">${message}</div>
            </div>
        `);
        $('#messages').append(messageDiv);
        scrollToBottom();
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        const indicator = $('<div class="typing-indicator bot-message"><span></span><span></span><span></span></div>');
        $('#messages').append(indicator);
        scrollToBottom();
    }
    
    // Function to hide typing indicator
    function hideTypingIndicator() {
        $('.typing-indicator').remove();
    }
    
    // Function to scroll chat to bottom
    function scrollToBottom() {
        const chatContainer = document.getElementById('chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Focus on input field
    $('#user-input').focus();
    
    // Function to start a new chat (clear session storage)
    window.startNewChat = function() {
        sessionStorage.removeItem('chatSessionActive');
        // Optionally clear the chat messages from the UI
        $('#messages').empty();
        // Add initial bot message
        addBotMessage("Hello! I am PoBot, your legal AI assistant. Which language would you like to continue the conversation with?");
        // Reset the new session flag
        startNewSession = true;
    };
});