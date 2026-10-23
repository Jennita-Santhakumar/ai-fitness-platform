import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav style={styles.nav}>
      <div style={styles.brand}>
        <Link to="/" style={styles.brandLink}>⚡ AI Fitness Platform</Link>
      </div>
      <div style={styles.links}>
        <Link to="/" style={styles.link}>Dashboard</Link>
        <Link to="/plans" style={styles.link}>Plans</Link>
        <Link to="/sessions" style={styles.link}>Sessions</Link>
        <Link to="/nutrition" style={styles.link}>Nutrition</Link>
      </div>
      <div style={styles.userSection}>
        {user ? (
          <>
            <span style={styles.userEmail}>{user.email}</span>
            <button onClick={handleLogout} style={styles.logoutBtn}>Logout</button>
          </>
        ) : (
          <Link to="/login" style={styles.loginLink}>Login</Link>
        )}
      </div>
    </nav>
  );
};

const styles = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 24px',
    backgroundColor: '#1f2937',
    color: '#ffffff',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  brand: {
    fontSize: '18px',
    fontWeight: 'bold',
  },
  brandLink: {
    color: '#ffffff',
    textDecoration: 'none',
  },
  links: {
    display: 'flex',
    gap: '20px',
  },
  link: {
    color: '#d1d5db',
    textDecoration: 'none',
    fontSize: '15px',
    fontWeight: '500',
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  userEmail: {
    fontSize: '14px',
    color: '#9ca3af',
  },
  logoutBtn: {
    padding: '6px 12px',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  loginLink: {
    color: '#3b82f6',
    textDecoration: 'none',
    fontWeight: '600',
  },
};
