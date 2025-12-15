import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import LoginPage from './components/LoginPage';
import AboutPage from './components/AboutPage';
import CategoryPage from './components/CategoryPage';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const handleLogout = () => {
    setIsAuthenticated(false);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/login" 
          element={
            isAuthenticated ? (
              <Navigate to="/about" replace />
            ) : (
              <LoginPage onLogin={() => setIsAuthenticated(true)} />
            )
          } 
        />
        <Route 
          path="/about" 
          element={
            isAuthenticated ? (
              <AboutPage onLogout={handleLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          } 
        />
        <Route 
          path="/category/:categoryName" 
          element={
            isAuthenticated ? (
              <CategoryPage onLogout={handleLogout} />
            ) : (
              <Navigate to="/login" replace />
            )
          } 
        />
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}