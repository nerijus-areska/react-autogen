
import React from 'react';
import { Route, Routes, BrowserRouter as Router } from 'react-router-dom';
import ScrollToTop from './components/ScrollToTop';
import TodoApp from './components/TodoApp';

function App() {
    return (
        <Router>
            <ScrollToTop />
            <Routes>
                <Route path="/" element={<TodoApp />} />
            </Routes>
        </Router>
    );
}

export default App;
