/**
 * components/Navbar.tsx
 * ---------------------
 * Top navigation bar with brand name and clickable profile dropdown.
 */

import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user, logout } = useAuth();
  const [open, setOpen]  = useState(false);
  const wrapperRef       = useRef<HTMLDivElement>(null);

  /* Close dropdown when clicking outside */
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = () => {
    setOpen(false);
    logout();
  };

  const capitalize = (s: string) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s;

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-icon">&#129657;</span>
        <span className="navbar-title">SymptoSense AI</span>
      </div>

      <nav className="navbar-links">
        <NavLink to="/dashboard" className={({ isActive }) => 'navbar-link' + (isActive ? ' navbar-link--active' : '')}>
          &#129657; Dashboard
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => 'navbar-link' + (isActive ? ' navbar-link--active' : '')}>
          &#128269; Search Engine
        </NavLink>
      </nav>

      <div className="navbar-right" ref={wrapperRef}>
        {user && (
          <>
          <button
            type="button"
            className="profile-btn"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open ? "true" : "false"}
            aria-haspopup="true"
            aria-controls="profile-menu"
          >
            <span className="profile-avatar">&#128100;</span>
            <span className="profile-username">{user.username}</span>
            <span className="profile-caret">{open ? '▲' : '▼'}</span>
          </button>

          <div id="profile-menu" className="profile-dropdown" hidden={!open}>
            <div className="profile-dropdown-header">
              <span className="profile-dropdown-icon">&#128100;</span>
              <span className="profile-dropdown-title">User Profile</span>
            </div>

            <div className="profile-info">
              <div className="profile-info-row">
                <span className="profile-info-label">Name</span>
                <span className="profile-info-value">{user.username}</span>
              </div>
              <div className="profile-info-row">
                <span className="profile-info-label">Email</span>
                <span className="profile-info-value profile-email">{user.email}</span>
              </div>
              <div className="profile-info-row">
                <span className="profile-info-label">Age</span>
                <span className="profile-info-value">{user.age}</span>
              </div>
              <div className="profile-info-row">
                <span className="profile-info-label">Gender</span>
                <span className="profile-info-value">{capitalize(user.gender)}</span>
              </div>
            </div>

            <div className="profile-divider" />

            <button type="button" className="profile-signout" onClick={handleLogout}>
              <span>&#128682;</span>
              Sign Out
            </button>
          </div>
          </>
        )}
      </div>
    </nav>
  );
}
