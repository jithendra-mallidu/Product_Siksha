import { useState, useRef, useEffect } from 'react';
import { Send, Plus, X, Loader2, Paperclip, Maximize2, Minimize2, Trash2 } from 'lucide-react';

interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    files?: { name: string; type: string; preview?: string }[];
    timestamp: Date;
}

interface FileAttachment {
    file: File;
    preview?: string;
    base64?: string;
}

interface ChatInterfaceProps {
    question: string;
    questionId: number;
    onSendMessage: (message: string, files: FileAttachment[]) => Promise<string>;
    isLoading: boolean;
}

export default function ChatInterface({ question, questionId, onSendMessage, isLoading }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [attachedFiles, setAttachedFiles] = useState<FileAttachment[]>([]);
    const [isSending, setIsSending] = useState(false);
    const [composeMode, setComposeMode] = useState(false); // When true, Enter creates new line instead of sending

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Load messages from localStorage when question changes
    useEffect(() => {
        const storageKey = `chat_messages_${questionId}`;
        const savedMessages = localStorage.getItem(storageKey);
        if (savedMessages) {
            try {
                const parsed = JSON.parse(savedMessages);
                // Restore Date objects for timestamps
                const restored = parsed.map((msg: ChatMessage) => ({
                    ...msg,
                    timestamp: new Date(msg.timestamp)
                }));
                setMessages(restored);
            } catch (e) {
                console.error('Error loading chat history:', e);
                setMessages([]);
            }
        } else {
            setMessages([]);
        }
        setInputValue('');
        setAttachedFiles([]);
    }, [questionId]);

    // Save messages to localStorage when they change
    useEffect(() => {
        if (messages.length > 0) {
            const storageKey = `chat_messages_${questionId}`;
            localStorage.setItem(storageKey, JSON.stringify(messages));
        }
    }, [messages, questionId]);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
        }
    }, [inputValue]);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);

        const newAttachments: FileAttachment[] = await Promise.all(
            files.map(async (file) => {
                const base64 = await fileToBase64(file);
                const preview = file.type.startsWith('image/')
                    ? URL.createObjectURL(file)
                    : undefined;
                return { file, preview, base64 };
            })
        );

        setAttachedFiles(prev => [...prev, ...newAttachments]);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const fileToBase64 = (file: File): Promise<string> => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = reject;
        });
    };

    const removeFile = (index: number) => {
        setAttachedFiles(prev => {
            const newFiles = [...prev];
            if (newFiles[index].preview) {
                URL.revokeObjectURL(newFiles[index].preview!);
            }
            newFiles.splice(index, 1);
            return newFiles;
        });
    };

    const handleSend = async () => {
        if ((!inputValue.trim() && attachedFiles.length === 0) || isSending) return;

        const userMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue,
            files: attachedFiles.map(f => ({
                name: f.file.name,
                type: f.file.type,
                preview: f.preview
            })),
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        const messageText = inputValue;
        const filesToSend = [...attachedFiles];
        setInputValue('');
        setAttachedFiles([]);
        setIsSending(true);

        try {
            const response = await onSendMessage(messageText, filesToSend);

            const assistantMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response,
                timestamp: new Date()
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            const errorMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Sorry, I encountered an error processing your request. Please try again.',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsSending(false);
            // Auto-focus the input field after receiving response
            // Use setTimeout to ensure focus happens after React re-render
            setTimeout(() => {
                textareaRef.current?.focus();
            }, 100);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            if (composeMode) {
                // In compose mode, Enter creates new line, Ctrl/Cmd+Enter sends
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    handleSend();
                }
                // Otherwise let the default Enter behavior (new line) happen
            } else {
                // Normal mode: Enter sends, Shift+Enter creates new line
                if (!e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                }
            }
        }
    };

    const clearChat = () => {
        const storageKey = `chat_messages_${questionId}`;
        localStorage.removeItem(storageKey);
        setMessages([]);
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-lg shadow-sm overflow-hidden">
            {/* Chat Header with Clear Button */}
            {messages.length > 0 && (
                <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
                    <span className="text-xs text-gray-500">
                        {messages.length} message{messages.length !== 1 ? 's' : ''}
                    </span>
                    <button
                        onClick={clearChat}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Clear chat history"
                    >
                        <Trash2 className="w-3 h-3" />
                        Clear
                    </button>
                </div>
            )}
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[400px] max-h-[500px]">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400">
                        <div className="w-16 h-16 mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                            <Send className="w-8 h-8" />
                        </div>
                        <p className="text-center text-sm">
                            Start a conversation about this question.<br />
                            Share your answer or ask for guidance.
                        </p>
                    </div>
                ) : (
                    messages.map((message) => (
                        <div
                            key={message.id}
                            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[80%] rounded-2xl px-4 py-3 ${message.role === 'user'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-800'
                                    }`}
                            >
                                {/* File attachments */}
                                {message.files && message.files.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mb-2">
                                        {message.files.map((file, idx) => (
                                            <div key={idx} className="flex items-center gap-1 px-2 py-1 bg-white/20 rounded text-xs">
                                                <Paperclip className="w-3 h-3" />
                                                {file.name}
                                            </div>
                                        ))}
                                    </div>
                                )}
                                {/* Message content */}
                                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                                    {message.content}
                                </div>
                            </div>
                        </div>
                    ))
                )}

                {/* Loading indicator */}
                {isSending && (
                    <div className="flex justify-start">
                        <div className="bg-gray-100 rounded-2xl px-4 py-3">
                            <div className="flex items-center gap-2 text-gray-500">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span className="text-sm">Thinking...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* File Previews */}
            {attachedFiles.length > 0 && (
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                    <div className="flex flex-wrap gap-2">
                        {attachedFiles.map((attachment, index) => (
                            <div
                                key={index}
                                className="relative group flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg"
                            >
                                {attachment.preview ? (
                                    <img src={attachment.preview} alt="" className="w-8 h-8 rounded object-cover" />
                                ) : (
                                    <Paperclip className="w-4 h-4 text-gray-400" />
                                )}
                                <span className="text-xs text-gray-600 max-w-[100px] truncate">
                                    {attachment.file.name}
                                </span>
                                <button
                                    onClick={() => removeFile(index)}
                                    className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Input Bar - Light Theme */}
            <div className="border-t border-gray-200 bg-white p-3">
                <div className="flex items-end gap-2">
                    {/* File Upload Button */}
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        className="flex-shrink-0 w-10 h-10 flex items-center justify-center text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors"
                        title="Attach file"
                    >
                        <Plus className="w-5 h-5" />
                    </button>
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        accept="image/*,.pdf,.doc,.docx,.txt"
                        onChange={handleFileSelect}
                        className="hidden"
                    />

                    {/* Text Input with Compose Mode Toggle inside */}
                    <div className="flex-1 bg-gray-100 rounded-2xl px-4 py-2 border border-gray-200 flex items-end gap-2">
                        <textarea
                            ref={textareaRef}
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={composeMode
                                ? "Type your message... (Ctrl+Enter to send)"
                                : "Ask about this question..."
                            }
                            rows={1}
                            className="flex-1 bg-transparent text-gray-800 placeholder-gray-400 resize-none outline-none text-sm leading-relaxed max-h-[150px]"
                            disabled={isSending}
                        />
                        {/* Compose Mode Toggle - inside input field */}
                        <button
                            onClick={() => setComposeMode(!composeMode)}
                            className={`flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full transition-colors ${composeMode
                                ? 'text-blue-600 bg-blue-100 hover:bg-blue-200'
                                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-200'
                                }`}
                            title={composeMode
                                ? 'Compose mode: Enter = new line, Ctrl+Enter = send'
                                : 'Normal mode: Enter = send, Shift+Enter = new line'
                            }
                        >
                            {composeMode ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                        </button>
                    </div>

                    {/* Send Button */}
                    <button
                        onClick={handleSend}
                        disabled={isSending || (!inputValue.trim() && attachedFiles.length === 0)}
                        className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {isSending ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Send className="w-5 h-5" />
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
