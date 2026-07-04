<template>
    <!-- Sidebar -->
    <div class="sidebar">
        <button class="new-chat-btn" @click="startNewChat">
            <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="16" width="16" xmlns="http://www.w3.org/2000/svg"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            新对话
        </button>
        <div class="task-list">
            <div class="task-item" 
                 v-for="task in tasks" 
                 :key="task.id"
                 :class="{ active: currentConvId === task.id }"
                 @click="loadChat(task.id)">
                <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="16" width="16" xmlns="http://www.w3.org/2000/svg"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                {{ task.title }}
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="chat-container" ref="chatContainer">
            
            <!-- Welcome Screen -->
            <div class="empty-state" v-if="messages.length === 0">
                <h1>Agent Chat</h1>
            </div>

            <!-- Messages -->
            <div class="message" v-for="(msg, index) in messages" :key="index" :class="{ bot: msg.role === 'assistant' }" @mouseenter="msg.hover = true" @mouseleave="msg.hover = false">
                <div class="avatar" :class="msg.role === 'assistant' ? 'bot-avatar' : 'user-avatar'">
                    {{ msg.role === 'assistant' ? '🤖' : 'U' }}
                </div>
                <div class="msg-content">
                    
                    <!-- Intermediate Steps -->
                    <div v-if="msg.steps && msg.steps.length > 0" class="intermediate-steps">
                        <div class="steps-toggle" @click="msg.showSteps = !msg.showSteps">
                            <span class="toggle-icon">
                                <svg v-if="msg.showSteps" stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="14" width="14"><polyline points="6 15 12 9 18 15"></polyline></svg>
                                <svg v-else stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="14" width="14"><polyline points="6 9 12 15 18 9"></polyline></svg>
                            </span>
                            中间思考与工具调用 ({{ msg.steps.length }} 步)
                        </div>
                        <div class="steps-content" v-show="msg.showSteps">
                            <div v-for="(step, sIdx) in msg.steps" :key="sIdx" class="step-item">
                                <div v-if="step.type === 'thinking'" class="step-thinking">
                                    <span class="step-icon">🤔 思考:</span> {{ step.content }}
                                </div>
                                <div v-if="step.type === 'tool_call'" class="step-tool-call" :class="step.result ? 'done' : 'running'">
                                    <span class="step-icon">🛠️ 调用:</span> {{ step.name }}({{ step.args }})
                                    <svg v-if="!step.result" class="spin" style="animation: spin 1s linear infinite;" stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="12" width="12" xmlns="http://www.w3.org/2000/svg"><line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line></svg>
                                </div>
                                <div v-if="step.type === 'tool_result' || (step.type === 'tool_call' && step.result)" class="step-tool-result">
                                    <span class="step-icon">✅ 返回:</span> {{ step.result }}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Message Text (Markdown) -->
                    <div v-html="renderMarkdown(msg.content)" v-if="msg.content"></div>
                    
                    <!-- Loading Cursor -->
                    <span v-if="msg.role === 'assistant' && msg.isLoading && !msg.content && (!msg.tool_calls || msg.tool_calls.length===0)" class="blink-cursor"></span>
                    
                    <!-- Message Actions -->
                    <div class="msg-actions" v-if="msg.hover && msg.seq_id !== undefined">
                        <button class="action-btn" title="引用此消息" @click="quoteMessage(msg)">
                            <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="14" width="14" xmlns="http://www.w3.org/2000/svg"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 2.1 0 3 .1L5 21z"></path><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 1 1 2 1z"></path></svg>
                        </button>
                    </div>
                </div>
            </div>

        </div>

        <!-- Input Area -->
        <div class="input-wrapper">
            <div class="quote-preview" v-if="quotedMessage">
                <div class="quote-content">
                    <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="14" width="14" xmlns="http://www.w3.org/2000/svg" style="margin-right: 5px;"><polyline points="15 10 20 15 15 20"></polyline><path d="M4 4v7a4 4 0 0 0 4 4h12"></path></svg>
                    引用: {{ quotedMessage.content.substring(0, 50) + (quotedMessage.content.length > 50 ? '...' : '') }}
                </div>
                <button class="cancel-quote" @click="cancelQuote" title="取消引用">✕</button>
            </div>
            <div class="input-box">
                <textarea 
                    v-model="inputMsg" 
                    placeholder="发送消息..." 
                    @keydown.enter.prevent="sendMessage"
                    @input="autoResize"
                    ref="inputBoxRef"
                    rows="1"
                    :disabled="isGenerating"
                ></textarea>
                <button class="send-btn" @click="sendMessage" :disabled="!inputMsg.trim() || isGenerating">
                    <svg v-if="!isGenerating" stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="16" width="16" xmlns="http://www.w3.org/2000/svg"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    <svg v-else style="animation: spin 1s linear infinite;" stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="16" width="16"><circle cx="12" cy="12" r="10"></circle><path d="M12 2v4"></path></svg>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import axios from 'axios';
import { marked } from 'marked';

const API_BASE = 'http://127.0.0.1:8000';

const tasks = ref([]);
const messages = ref([]);
const inputMsg = ref('');
const currentConvId = ref(null);
const isGenerating = ref(false);
const chatContainer = ref(null);
const inputBoxRef = ref(null);
const quotedMessage = ref(null);

// Fetch task list
const fetchTasks = async () => {
    try {
        const res = await axios.get(`${API_BASE}/tasks`);
        if (res.data.code === 0) {
            tasks.value = res.data.data;
        }
    } catch (err) {
        console.error("Failed to fetch tasks", err);
    }
};

// Load a specific chat
const loadChat = async (convId) => {
    if (isGenerating.value) return;
    currentConvId.value = convId;
    messages.value = [];
    
    try {
        const res = await axios.get(`${API_BASE}/tasks/${convId}?page=1&page_size=100`);
        if (res.data.code === 0) {
            const loadedMessages = [];
            let currentAssistantMsg = null;
            
            for (const m of res.data.data.messages) {
                if (m.role === 'user') {
                    loadedMessages.push({ role: 'user', content: m.content, seq_id: m.seq_id, hover: false });
                    currentAssistantMsg = null;
                } else {
                    if (!currentAssistantMsg) {
                        currentAssistantMsg = { role: 'assistant', content: '', seq_id: m.seq_id, hover: false, steps: [], showSteps: false };
                        loadedMessages.push(currentAssistantMsg);
                    }
                    if (m.msg_type === 'thinking') {
                        currentAssistantMsg.steps.push({ type: 'thinking', content: m.content });
                    } else if (m.msg_type === 'tool_call') {
                        try {
                            const tc = JSON.parse(m.content);
                            currentAssistantMsg.steps.push({ type: 'tool_call', name: tc.function.name, args: tc.function.arguments, result: null });
                        } catch(e) {}
                    } else if (m.msg_type === 'tool_result') {
                        try {
                            const tr = JSON.parse(m.content);
                            const lastTool = currentAssistantMsg.steps.find(t => t.type === 'tool_call' && t.result === null);
                            if (lastTool) {
                                lastTool.result = tr.result;
                            } else {
                                currentAssistantMsg.steps.push({ type: 'tool_result', result: tr.result });
                            }
                        } catch(e) {}
                    } else if (m.msg_type === 'normal') {
                        currentAssistantMsg.content = m.content;
                        currentAssistantMsg.seq_id = m.seq_id;
                    }
                }
            }
            messages.value = loadedMessages;
            scrollToBottom();
        }
    } catch (err) {
        console.error("Failed to load chat", err);
    }
};

const startNewChat = () => {
    if (isGenerating.value) return;
    currentConvId.value = null;
    messages.value = [];
    inputMsg.value = '';
    quotedMessage.value = null;
};

const quoteMessage = (msg) => {
    quotedMessage.value = msg;
    inputBoxRef.value?.focus();
};

const cancelQuote = () => {
    quotedMessage.value = null;
};

const scrollToBottom = () => {
    nextTick(() => {
        if (chatContainer.value) {
            chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
        }
    });
};

const autoResize = () => {
    const el = inputBoxRef.value;
    if (el) {
        el.style.height = 'auto';
        el.style.height = (el.scrollHeight) + 'px';
    }
};

const renderMarkdown = (text) => {
    if (!text) return '';
    return marked.parse(text);
};

const sendMessage = async () => {
    const text = inputMsg.value.trim();
    if (!text || isGenerating.value) return;

    messages.value.push({ role: 'user', content: text });
    inputMsg.value = '';
    autoResize();
    isGenerating.value = true;
    scrollToBottom();

    const botMsg = {
        role: 'assistant',
        content: '',
        steps: [],
        showSteps: true,
        isLoading: true
    };
    messages.value.push(botMsg);

    try {
        const payload = {
            goal: text,
            conv_id: currentConvId.value
        };
        if (quotedMessage.value) {
            payload.quote_seq = quotedMessage.value.seq_id;
        }

        const response = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        quotedMessage.value = null;

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.replace('data: ', '').trim();
                    if (!jsonStr) continue;
                    
                    try {
                        const event = JSON.parse(jsonStr);
                        handleStreamEvent(event, botMsg);
                    } catch (e) {
                        console.error("Error parsing SSE JSON:", e, jsonStr);
                    }
                }
            }
        }
    } catch (err) {
        console.error("Stream error:", err);
        botMsg.content += "\n\n**[Error] Failed to communicate with server.**";
    } finally {
        botMsg.isLoading = false;
        isGenerating.value = false;
        fetchTasks();
        scrollToBottom();
    }
};

const handleStreamEvent = (event, botMsg) => {
    switch (event.type) {
        case 'conversation_id':
            if (!currentConvId.value) {
                currentConvId.value = event.data;
            }
            break;
        case 'content':
            botMsg.content += event.data;
            scrollToBottom();
            break;
        case 'thinking':
            botMsg.steps.push({ type: 'thinking', content: event.data });
            scrollToBottom();
            break;
        case 'tool_call':
            botMsg.steps.push({
                type: 'tool_call',
                name: event.data.name,
                args: event.data.arguments,
                result: null
            });
            scrollToBottom();
            break;
        case 'tool_result':
            const tool = botMsg.steps.find(t => t.type === 'tool_call' && t.name === event.data.name && t.result === null);
            if (tool) {
                tool.result = event.data.result;
            } else {
                botMsg.steps.push({ type: 'tool_result', result: event.data.result });
            }
            scrollToBottom();
            break;
        case 'done':
            botMsg.isLoading = false;
            botMsg.showSteps = false;
            break;
        case 'error':
            botMsg.content += `\n\n**[Error]** ${event.data}`;
            botMsg.isLoading = false;
            break;
    }
};

onMounted(() => {
    fetchTasks();
});
</script>

<style scoped>
/* ---------- Sidebar ---------- */
.sidebar {
    width: 260px;
    background-color: var(--sidebar-bg);
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border-color);
    transition: width 0.3s ease;
}
.new-chat-btn {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 10px;
    padding: 12px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: transparent;
    color: white;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.2s;
}
.new-chat-btn:hover {
    background-color: var(--sidebar-hover);
}
.task-list {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
}
.task-item {
    padding: 12px;
    margin-bottom: 5px;
    border-radius: 6px;
    cursor: pointer;
    color: var(--text-main);
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: background 0.2s;
}
.task-item:hover, .task-item.active {
    background-color: var(--sidebar-hover);
}

/* ---------- Main Chat Area ---------- */
.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: var(--chat-bg);
    position: relative;
}
.chat-container {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 120px; /* Space for input */
}
.message {
    padding: 24px 10%;
    display: flex;
    gap: 20px;
    line-height: 1.6;
    font-size: 15px;
    color: var(--text-main);
    position: relative;
}
.message.bot {
    background-color: var(--bot-msg-bg);
    border-top: 1px solid rgba(0,0,0,0.1);
    border-bottom: 1px solid rgba(0,0,0,0.1);
}
.avatar {
    width: 30px;
    height: 30px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    flex-shrink: 0;
}
.user-avatar { background-color: #5436da; color: white; }
.bot-avatar { background-color: #10a37f; color: white; }
.msg-content {
    flex: 1;
    word-wrap: break-word;
    overflow: hidden;
}
.msg-actions {
    position: absolute;
    right: 10%;
    top: 24px;
    display: flex;
    gap: 8px;
}
.action-btn {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: var(--text-muted);
    border-radius: 4px;
    padding: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}
.action-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: var(--text-main);
}

/* Markdown Styles */
:deep(.msg-content p) { margin-bottom: 10px; }
:deep(.msg-content pre) {
    background: #000;
    padding: 10px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 10px 0;
    color: #e5e5e5;
}
:deep(.msg-content code) {
    font-family: Consolas, Monaco, monospace;
    background: rgba(255,255,255,0.1);
    padding: 2px 4px;
    border-radius: 4px;
}
:deep(.msg-content pre code) { background: transparent; padding: 0; }
:deep(.msg-content a) { color: #3b82f6; }

/* ---------- Intermediate Steps ---------- */
.intermediate-steps {
    margin-bottom: 15px;
    background: rgba(0,0,0,0.15);
    border-radius: 6px;
    overflow: hidden;
}
.steps-toggle {
    padding: 10px 14px;
    font-size: 13px;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
    transition: background 0.2s;
}
.steps-toggle:hover {
    background: rgba(0,0,0,0.1);
    color: var(--text-main);
}
.steps-content {
    padding: 0 14px 14px 14px;
    border-top: 1px solid rgba(255,255,255,0.05);
}
.step-item {
    font-size: 13px;
    margin-top: 10px;
    color: #c9d1d9;
    background: rgba(255,255,255,0.03);
    padding: 8px;
    border-radius: 4px;
    border-left: 2px solid transparent;
}
.step-icon {
    font-weight: 500;
    margin-right: 4px;
    color: #8b949e;
}
.step-thinking { border-left-color: #8b949e; }
.step-tool-call { border-left-color: #eab308; }
.step-tool-result { border-left-color: #10a37f; }
.step-tool-call.done { border-left-color: #10a37f; }

/* ---------- Input Area ---------- */
.input-wrapper {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 20px 10%;
    background: linear-gradient(180deg, rgba(53,55,64,0), var(--chat-bg) 30%);
}
.quote-preview {
    background-color: #2a2b32;
    border-left: 3px solid #10a37f;
    border-radius: 6px 6px 0 0;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: -6px;
    z-index: 0;
    position: relative;
}
.quote-content {
    display: flex;
    align-items: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: 20px;
}
.cancel-quote {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 14px;
}
.cancel-quote:hover { color: white; }
.input-box {
    position: relative;
    z-index: 1;
    background-color: #40414f;
    border-radius: 12px;
    border: 1px solid var(--border-color);
    box-shadow: 0 0 15px rgba(0,0,0,0.1);
    display: flex;
    align-items: flex-end;
    padding: 10px 14px;
}
.input-box:focus-within {
    border-color: #565869;
    box-shadow: 0 0 15px rgba(0,0,0,0.2);
}
.input-box textarea {
    flex: 1;
    background: transparent;
    border: none;
    color: white;
    font-size: 16px;
    resize: none;
    outline: none;
    max-height: 200px;
    min-height: 24px;
    padding: 0;
    line-height: 24px;
}
.send-btn {
    background-color: var(--primary);
    color: white;
    border: none;
    border-radius: 6px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.2s;
    flex-shrink: 0;
    margin-left: 10px;
}
.send-btn:hover:not(:disabled) {
    background-color: var(--primary-hover);
}
.send-btn:disabled {
    background-color: transparent;
    color: var(--text-muted);
    cursor: not-allowed;
}

/* Empty State */
.empty-state {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-main);
}
.empty-state h1 { font-size: 2.5rem; font-weight: 600; margin-bottom: 40px; }

/* Animations */
.blink-cursor {
    display: inline-block;
    width: 8px;
    height: 16px;
    background: #fff;
    animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
