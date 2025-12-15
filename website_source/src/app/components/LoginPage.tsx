import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { ImageWithFallback } from './figma/ImageWithFallback';

import { API_BASE } from '../config';

interface LoginPageProps {
  onLogin: () => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'login' | 'signup' | 'change-password'>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const navigate = useNavigate();


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (mode === 'change-password') {
        const response = await fetch(`${API_BASE}/change-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, current_password: password, new_password: newPassword })
        });
        const data = await response.json();

        if (response.ok) {
          setSuccess(data.message);
          setMode('login');
          setPassword('');
          setNewPassword('');
        } else {
          setError(data.error || 'Password update failed');
        }
      } else {
        const endpoint = mode === 'signup' ? '/signup' : '/login';
        const response = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
          // Store token in localStorage
          localStorage.setItem('token', data.token);
          localStorage.setItem('user', JSON.stringify(data.user));
          onLogin();
          navigate('/about');
        } else {
          setError(data.error || 'Authentication failed');
        }
      }
    } catch (err) {
      setError('Unable to connect to server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Left side - Login Form */}
      <div className="w-[35%] flex flex-col justify-center px-12 bg-white">
        <div className="max-w-md mx-auto w-full">
          <div className="mb-8">
            <h1 className="text-3xl mb-2">Product Siksha</h1>
            <p className="text-gray-600">Master PM Interviews with AI-Powered Feedback</p>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-1">
              {mode === 'signup' ? 'Create Account' : mode === 'change-password' ? 'Change Password' : 'Welcome Back'}
            </h2>
            <p className="text-sm text-gray-500">
              {mode === 'signup' ? 'Sign up to get started' : mode === 'change-password' ? 'Enter your details to update password' : 'Please enter your details to sign in'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                {error}
              </div>
            )}
            {success && (
              <div className="p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
                {success}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block mb-2">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your email"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block mb-2">
                {mode === 'change-password' ? 'Current Password' : 'Password'}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
                  placeholder={mode === 'signup' ? "Create a password (min 6 chars)" : mode === 'change-password' ? "Enter current password" : "Enter your password"}
                  required
                  minLength={mode === 'signup' ? 6 : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {mode === 'change-password' && (
              <div>
                <label htmlFor="newPassword" className="block mb-2">
                  New Password
                </label>
                <div className="relative">
                  <input
                    id="newPassword"
                    type={showNewPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
                    placeholder="Enter new password (min 6 chars)"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
                  >
                    {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Processing...' : mode === 'signup' ? 'Sign Up' : mode === 'change-password' ? 'Update Password' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-600 space-y-2">
            <p>
              {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button
                onClick={() => {
                  setMode(mode === 'login' ? 'signup' : 'login');
                  setError('');
                  setSuccess('');
                  setNewPassword('');
                }}
                className="text-blue-600 hover:underline font-medium"
              >
                {mode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </p>
            {mode === 'login' && (
              <p>
                <button
                  onClick={() => {
                    setMode('change-password');
                    setError('');
                    setSuccess('');
                    setNewPassword('');
                  }}
                  className="text-gray-500 hover:text-blue-600 hover:underline"
                >
                  Change Password
                </button>
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Right side - Image */}
      <div className="flex-1 relative bg-gray-100">
        <div className="absolute inset-0 bg-black/40">
          <ImageWithFallback
            src="https://images.unsplash.com/photo-1591201417943-d82df759897d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxwcm9kdWN0JTIwbWFuYWdlciUyMHdvcmtzcGFjZXxlbnwxfHx8fDE3NjU2Nzc3OTZ8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
            alt="Product Manager Workspace"
            className="w-full h-full object-cover"
          />
        </div>
        <div className="absolute inset-0 flex items-center justify-center text-white p-12">
          <div className="max-w-lg text-center">
            <h2 className="text-4xl mb-4">Prepare. Practice. Perfect.</h2>
            <p className="text-lg opacity-90">
              Your AI companion for mastering product management interview questions
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
