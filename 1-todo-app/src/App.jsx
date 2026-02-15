
import React, { useEffect } from 'react';
import { Route, Routes, BrowserRouter as Router } from 'react-router-dom';
import ScrollToTop from './components/ScrollToTop';
import TodoApp from './components/TodoApp';
import ChatOverlay from './overlay/ChatOverlay';

function App() {
    useEffect(() => {
        const sessionId = new URLSearchParams(window.location.search).get('session_id');
        if (sessionId) {
            localStorage.setItem('session_id', sessionId);
        }
    }, []);

    return (
        <Router>
            <ScrollToTop />
            <Routes>
                <Route path="/" element={<TodoApp />} />
            </Routes>
            <ChatOverlay />
        </Router>
    );
}

export default App;
