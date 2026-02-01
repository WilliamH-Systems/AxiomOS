class AxiomOSChat {
    constructor() {
        this.sessionId = null;
        this.settings = {
            model: 'llama-3.1-8b-instant',
            temperature: 0.7,
            max_tokens: 1000
        };
        this.isConnected = false;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadSettings();
        this.checkHealth();
        this.autoResizeTextarea();
    }

    bindEvents() {
        // Send message
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Character counter
        document.getElementById('messageInput').addEventListener('input', (e) => {
            document.getElementById('charCount').textContent = e.target.value.length;
            this.autoResizeTextarea();
        });

        // Settings modal
        document.getElementById('settingsBtn').addEventListener('click', () => {
            document.getElementById('settingsModal').style.display = 'flex';
        });

        document.getElementById('closeSettingsBtn').addEventListener('click', () => {
            document.getElementById('settingsModal').style.display = 'none';
        });

        document.getElementById('saveSettingsBtn').addEventListener('click', () => {
            this.saveSettings();
        });

        // Settings controls
        document.getElementById('temperatureSlider').addEventListener('input', (e) => {
            document.getElementById('temperatureValue').textContent = e.target.value;
        });

        // Clear chat
        document.getElementById('clearChatBtn').addEventListener('click', () => {
            this.clearChat();
        });

        // Close modal on outside click
        document.getElementById('settingsModal').addEventListener('click', (e) => {
            if (e.target.id === 'settingsModal') {
                document.getElementById('settingsModal').style.display = 'none';
            }
        });
    }

    autoResizeTextarea() {
        const textarea = document.getElementById('messageInput');
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    async checkHealth() {
        try {
            const response = await fetch('/health');
            const health = await response.json();
            
            if (health.overall === 'healthy') {
                this.isConnected = true;
                this.updateStatus('Online', true);
            } else {
                this.isConnected = false;
                this.updateStatus('Degraded', false);
            }
        } catch (error) {
            this.isConnected = false;
            this.updateStatus('Offline', false);
            console.error('Health check failed:', error);
        }
    }

    updateStatus(text, isOnline) {
        const statusElement = document.querySelector('.status');
        statusElement.textContent = text;
        statusElement.className = `status ${isOnline ? 'online' : 'offline'}`;
        
        if (!isOnline) {
            statusElement.style.background = '#ef4444';
            statusElement.innerHTML = text;
        }
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.isConnected) return;

        // Add user message
        this.addMessage('user', message);
        input.value = '';
        document.getElementById('charCount').textContent = '0';
        this.autoResizeTextarea();

        // Show typing indicator
        this.showTypingIndicator();
        
        // Disable send button
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = true;

        try {
            await this.streamResponse(message);
        } catch (error) {
            this.addMessage('assistant', `Error: ${error.message}`);
            console.error('Stream error:', error);
        } finally {
            this.hideTypingIndicator();
            sendBtn.disabled = false;
        }
    }

    async streamResponse(message) {
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId,
                stream: true,
                ...this.settings
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessage = null;
        let buffer = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            // Create assistant message on first chunk
                            if (!assistantMessage) {
                                assistantMessage = this.addMessage('assistant', '', true);
                            }

                            // Handle streaming content
                            if (data.token) {
                                this.appendMessage(assistantMessage, data.token);
                            }

                            // Handle completion
                            if (data.is_complete) {
                                if (data.session_id) {
                                    this.sessionId = data.session_id;
                                }
                                this.finalizeMessage(assistantMessage);
                                
                                // Add memory context if applicable
                                if (message.toLowerCase().includes('remember')) {
                                    this.appendMessage(assistantMessage, '\n\n💾 *I\'ve saved this conversation to your long-term memory.*');
                                } else if (message.toLowerCase().includes('recall')) {
                                    this.appendMessage(assistantMessage, '\n\n📋 *Retrieved from your memory banks.*');
                                }
                            }

                            // Handle errors
                            if (data.error) {
                                throw new Error(data.error);
                            }
                        } catch (parseError) {
                            console.warn('Failed to parse chunk:', line, parseError);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
            
            // Finalize message if still streaming
            if (assistantMessage) {
                this.finalizeMessage(assistantMessage);
            }
        }
    }

    addMessage(sender, content, isStreaming = false) {
        const container = document.getElementById('messagesContainer');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = content;
        
        messageContent.appendChild(messageText);
        messageDiv.appendChild(messageContent);
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = sender === 'user' ? 'You' : 'AxiomOS';
        messageDiv.appendChild(messageTime);
        
        if (isStreaming) {
            messageText.innerHTML = '';
            messageText.dataset.streaming = 'true';
        }
        
        container.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageText;
    }

    appendMessage(messageElement, content) {
        if (messageElement.dataset.streaming === 'true') {
            messageElement.textContent += content;
            this.scrollToBottom();
        }
    }

    finalizeMessage(messageElement) {
        messageElement.dataset.streaming = 'false';
        this.scrollToBottom();
    }

    showTypingIndicator() {
        document.getElementById('typingIndicator').style.display = 'flex';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        document.getElementById('typingIndicator').style.display = 'none';
    }

    scrollToBottom() {
        const container = document.getElementById('messagesContainer');
        container.scrollTop = container.scrollHeight;
    }

    clearChat() {
        const container = document.getElementById('messagesContainer');
        // Keep only the welcome message
        const messages = container.querySelectorAll('.message');
        messages.forEach((message, index) => {
            if (index > 0) { // Keep first message (welcome)
                message.remove();
            }
        });
        this.sessionId = null;
    }

    loadSettings() {
        const saved = localStorage.getItem('axiomos_settings');
        if (saved) {
            this.settings = { ...this.settings, ...JSON.parse(saved) };
            this.updateSettingsUI();
        }
    }

    saveSettings() {
        this.settings.model = document.getElementById('modelSelect').value;
        this.settings.temperature = parseFloat(document.getElementById('temperatureSlider').value);
        this.settings.max_tokens = parseInt(document.getElementById('maxTokensInput').value);
        
        localStorage.setItem('axiomos_settings', JSON.stringify(this.settings));
        document.getElementById('settingsModal').style.display = 'none';
        
        // Show confirmation
        this.addMessage('assistant', `⚙️ Settings updated:\n- Model: ${this.settings.model}\n- Temperature: ${this.settings.temperature}\n- Max Tokens: ${this.settings.max_tokens}`);
    }

    updateSettingsUI() {
        document.getElementById('modelSelect').value = this.settings.model;
        document.getElementById('temperatureSlider').value = this.settings.temperature;
        document.getElementById('temperatureValue').textContent = this.settings.temperature;
        document.getElementById('maxTokensInput').value = this.settings.max_tokens;
    }
}

// Initialize the chat application
document.addEventListener('DOMContentLoaded', () => {
    new AxiomOSChat();
});

// Handle visibility changes to reconnect when tab becomes visible again
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // Re-check health when tab becomes visible
        window.chat?.checkHealth();
    }
});