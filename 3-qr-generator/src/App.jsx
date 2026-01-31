
import React from 'react';
import { Route, Routes, BrowserRouter as Router } from 'react-router-dom';
import ScrollToTop from './components/ScrollToTop';
import QRCodeGenerator from './components/QRCodeGenerator';

function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<QRCodeGenerator />} />
      </Routes>
    </Router>
  );
}

export default App;
