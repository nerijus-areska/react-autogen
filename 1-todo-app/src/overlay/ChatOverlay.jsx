import React, { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, Send, X, Loader2, Crosshair } from 'lucide-react';

const API_URL = 'http://localhost:8000/api/v1/editor';

const OVERLAY_ATTR = 'data-chat-overlay';
const STORAGE_KEY_POS = 'chat_overlay_position';
const STORAGE_KEY_NOTIF = 'chat_overlay_notification';

function loadFromStorage(key, fallback) {
    try {
        const raw = sessionStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
    } catch {
        return fallback;
    }
}

function identifyElement(el) {
    const tag = el.tagName.toLowerCase();

    // Try to extract a human-readable label
    // 1. aria-label
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel) return `${tag}: "${ariaLabel}"`;

    // 2. For buttons/links: visible text content (direct or nested)
    if (tag === 'button' || tag === 'a' || el.getAttribute('role') === 'button') {
        const text = el.textContent?.trim();
        if (text && text.length < 60) return `${tag}: "${text}"`;
    }

    // 3. For inputs: placeholder or label
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
        const placeholder = el.getAttribute('placeholder');
        if (placeholder) return `${tag}: placeholder="${placeholder}"`;
        const id = el.id;
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (label) return `${tag}: label="${label.textContent.trim()}"`;
        }
    }

    // 4. For images: alt text
    if (tag === 'img') {
        const alt = el.getAttribute('alt');
        if (alt) return `${tag}: alt="${alt}"`;
    }

    // 5. Short text content for any element
    const text = el.textContent?.trim();
    if (text && text.length < 40) return `${tag}: "${text}"`;

    // 6. Fallback to id or class
    if (el.id) return `${tag}#${el.id}`;
    const cls = el.className;
    if (typeof cls === 'string' && cls.trim()) {
        const short = cls.trim().split(/\s+/).slice(0, 3).join('.');
        return `${tag}.${short}`;
    }

    return tag;
}

function ChatOverlay() {
    const [position, setPosition] = useState(() => loadFromStorage(STORAGE_KEY_POS, { x: 20, y: 20 }));
    const [isDragging, setIsDragging] = useState(false);
    const [message, setMessage] = useState('');
    const [sending, setSending] = useState(false);
    const [selecting, setSelecting] = useState(false);
    const [selectedElement, setSelectedElement] = useState(null);
    const [notification, setNotification] = useState(() => loadFromStorage(STORAGE_KEY_NOTIF, null));
    const dragOffset = useRef({ x: 0, y: 0 });
    const notificationTimer = useRef(null);
    const highlightedEl = useRef(null);
    const selectCleanup = useRef(null);

    // Persist position to sessionStorage on drag
    useEffect(() => {
        sessionStorage.setItem(STORAGE_KEY_POS, JSON.stringify(position));
    }, [position]);

    // Persist notification to sessionStorage, and start auto-dismiss timer on restore
    useEffect(() => {
        if (notification) {
            sessionStorage.setItem(STORAGE_KEY_NOTIF, JSON.stringify(notification));
            if (notificationTimer.current) clearTimeout(notificationTimer.current);
            notificationTimer.current = setTimeout(() => {
                setNotification(null);
                sessionStorage.removeItem(STORAGE_KEY_NOTIF);
            }, 15000);
        } else {
            sessionStorage.removeItem(STORAGE_KEY_NOTIF);
        }
    }, [notification]);

    const handlePointerDown = (e) => {
        if (e.target.closest('[data-no-drag]')) return;
        setIsDragging(true);
        dragOffset.current = {
            x: e.clientX - position.x,
            y: e.clientY - position.y,
        };
        e.currentTarget.setPointerCapture(e.pointerId);
    };

    const handlePointerMove = (e) => {
        if (!isDragging) return;
        setPosition({
            x: e.clientX - dragOffset.current.x,
            y: e.clientY - dragOffset.current.y,
        });
    };

    const handlePointerUp = () => {
        setIsDragging(false);
    };

    const showNotification = (text, isError = false) => {
        setNotification({ text, isError });
    };

    const clearHighlight = useCallback(() => {
        if (highlightedEl.current) {
            highlightedEl.current.style.outline = '';
            highlightedEl.current.style.outlineOffset = '';
            highlightedEl.current = null;
        }
    }, []);

    const exitSelectMode = useCallback(() => {
        clearHighlight();
        if (selectCleanup.current) {
            selectCleanup.current();
            selectCleanup.current = null;
        }
        setSelecting(false);
        document.body.style.cursor = '';
    }, [clearHighlight]);

    const handleSelect = () => {
        if (selecting) {
            exitSelectMode();
            return;
        }

        setSelecting(true);
        document.body.style.cursor = 'crosshair';

        const onMouseMove = (e) => {
            const el = document.elementFromPoint(e.clientX, e.clientY);
            if (!el || el.closest(`[${OVERLAY_ATTR}]`)) {
                clearHighlight();
                return;
            }
            if (el === highlightedEl.current) return;
            clearHighlight();
            highlightedEl.current = el;
            el.style.outline = '2px solid #f97316';
            el.style.outlineOffset = '2px';
        };

        const onClick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();

            const el = document.elementFromPoint(e.clientX, e.clientY);
            if (!el || el.closest(`[${OVERLAY_ATTR}]`)) return;

            const label = identifyElement(el);

            exitSelectMode();
            setSelectedElement(label);
        };

        const onKeyDown = (e) => {
            if (e.key === 'Escape') exitSelectMode();
        };

        document.addEventListener('mousemove', onMouseMove, true);
        document.addEventListener('click', onClick, true);
        document.addEventListener('keydown', onKeyDown, true);

        selectCleanup.current = () => {
            document.removeEventListener('mousemove', onMouseMove, true);
            document.removeEventListener('click', onClick, true);
            document.removeEventListener('keydown', onKeyDown, true);
        };
    };

    const handleSend = async () => {
        if (!message.trim() || sending) return;
        const sessionId = localStorage.getItem('session_id');
        const instruction = selectedElement
            ? `${message}\nUser selected element: "${selectedElement}"`
            : message;
        setMessage('');
        setSelectedElement(null);
        setSending(true);

        try {
            const res = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, instruction }),
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            showNotification(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
        } catch (err) {
            showNotification(`Error: ${err.message}`, true);
        } finally {
            setSending(false);
        }
    };

    return (
        <>
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3 }}
                style={{
                    position: 'fixed',
                    left: position.x,
                    top: position.y,
                    zIndex: 9999,
                    cursor: isDragging ? 'grabbing' : 'grab',
                    touchAction: 'none',
                }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                className="w-[30rem] rounded-xl bg-white shadow-2xl border border-gray-200 select-none"
                {...{ [OVERLAY_ATTR]: true }}
            >
                {/* Header */}
                <div className="flex items-center gap-2 px-4 py-3 rounded-t-xl bg-gradient-to-r from-red-500 to-orange-400 text-white">
                    <MessageCircle size={18} />
                    <span className="text-sm font-semibold">Chat</span>
                </div>

                {/* Input area */}
                <div className="flex items-center gap-2 p-3" data-no-drag>
                    <input
                        type="text"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder={sending ? 'Sending...' : 'Type a message...'}
                        disabled={sending}
                        className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-black outline-none focus:border-orange-400 focus:ring-1 focus:ring-orange-400 disabled:opacity-50"
                        style={{ cursor: 'text' }}
                    />
                    <button
                        onClick={handleSelect}
                        title="Select"
                        className={`flex items-center justify-center rounded-lg border p-2 transition-colors ${selecting ? 'border-orange-400 bg-orange-50 text-orange-600' : 'border-gray-300 text-gray-600 hover:bg-gray-100'}`}
                        data-no-drag
                    >
                        <Crosshair size={16} />
                    </button>
                    <button
                        onClick={handleSend}
                        disabled={sending}
                        className="flex items-center justify-center rounded-lg bg-gradient-to-r from-red-500 to-orange-400 p-2 text-white hover:opacity-90 transition-opacity disabled:opacity-50"
                        data-no-drag
                    >
                        <Send size={16} />
                    </button>
                </div>

                {/* Selected element label */}
                {selectedElement && (
                    <div className="flex items-center gap-1 px-3 pb-2 -mt-1" data-no-drag>
                        <Crosshair size={12} className="text-orange-500 shrink-0" />
                        <span className="text-xs text-gray-500 truncate">{selectedElement}</span>
                        <button onClick={() => setSelectedElement(null)} className="ml-auto text-gray-400 hover:text-gray-600">
                            <X size={12} />
                        </button>
                    </div>
                )}
            </motion.div>

            {/* Full-page loading overlay */}
            <AnimatePresence>
                {sending && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                    >
                        <div className="flex flex-col items-center gap-3">
                            <Loader2 size={48} className="animate-spin text-white" />
                            <span className="text-white text-lg font-semibold">Processing...</span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Bottom notification */}
            <AnimatePresence>
                {notification && (
                    <motion.div
                        initial={{ opacity: 0, y: 50 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 50 }}
                        transition={{ duration: 0.3 }}
                        className="fixed bottom-4 left-4 right-4 z-[10000] max-h-[50vh] overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-2xl"
                    >
                        <div className={`flex items-center justify-between px-4 py-2 rounded-t-xl text-white text-sm font-semibold ${notification.isError ? 'bg-red-600' : 'bg-gradient-to-r from-red-500 to-orange-400'}`}>
                            <span>{notification.isError ? 'Error' : 'Response'}</span>
                            <button onClick={() => { setNotification(null); sessionStorage.removeItem(STORAGE_KEY_NOTIF); }} className="hover:opacity-75">
                                <X size={16} />
                            </button>
                        </div>
                        <pre className="p-4 text-sm text-black whitespace-pre-wrap break-words font-sans">
                            {notification.text}
                        </pre>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}

export default ChatOverlay;
