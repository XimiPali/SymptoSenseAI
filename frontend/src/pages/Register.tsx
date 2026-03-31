/**
 * pages/Register.tsx  --  v2
 * Added: gender (radio buttons) and age (number input)
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

export default function Register() {
  const { login } = useAuth();
  const navigate  = useNavigate();

  const [form, setForm] = useState({
    username: '',
    email:    '',
    password: '',
    confirm:  '',
    gender:   'male' as 'male' | 'female',
    age:      25,
  });
  const [error,   setError]   = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value,
    }));
    setError('');
  };

  const validate = (): string => {
    if (!form.username || !form.email || !form.password || !form.confirm)
      return 'Please fill in all fields.';
    if (form.password.length < 6)
      return 'Password must be at least 6 characters.';
    if (form.password !== form.confirm)
      return 'Passwords do not match.';
    if (form.age < 0 || form.age > 120)
      return 'Age must be between 0 and 120.';
    return '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) { setError(err); return; }

    setLoading(true);
    try {
      await authAPI.register({
        username: form.username,
        email:    form.email,
        password: form.password,
        gender:   form.gender,
        age:      form.age,
      });
      const loginRes = await authAPI.login({ username: form.username, password: form.password });
      await login(loginRes.data.access_token);
      navigate('/dashboard');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div className="auth-header">
          <div className="auth-logo">&#127973;</div>
          <h1>SymptoSense AI</h1>
          <p>Create your account</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error error-text">{error}</div>}

          <div className="form-group">
            <label className="form-label" htmlFor="username">Username</label>
            <input id="username" name="username" type="text"
              className="form-input" placeholder="Choose a username"
              value={form.username} onChange={handleChange} />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="email">Email</label>
            <input id="email" name="email" type="email"
              className="form-input" placeholder="your@email.com"
              value={form.email} onChange={handleChange} />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="age">Age</label>
            <input id="age" name="age" type="number"
              className="form-input" placeholder="0 - 120"
              min={0} max={120}
              value={form.age} onChange={handleChange} />
          </div>

          <div className="form-group">
            <span className="form-label">Gender</span>
            <div className="gender-options">
              {(['male', 'female'] as const).map((g) => (
                <label key={g} className="gender-label">
                  <input type="radio" name="gender" value={g}
                    checked={form.gender === g} onChange={handleChange} />
                  {g.charAt(0).toUpperCase() + g.slice(1)}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input id="password" name="password" type="password"
              className="form-input" placeholder="At least 6 characters"
              value={form.password} onChange={handleChange} />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirm">Confirm Password</label>
            <input id="confirm" name="confirm" type="password"
              className="form-input" placeholder="Repeat your password"
              value={form.confirm} onChange={handleChange} />
          </div>

          <button type="submit" className="btn btn-primary auth-btn" disabled={loading}>
            {loading ? 'Creating account\u2026' : 'Create Account'}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
