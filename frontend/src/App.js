import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';
import Cookies from 'js-cookie';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Create AuthContext
const AuthContext = createContext();

// Auth Provider Component
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = Cookies.get('access_token');
      if (token) {
        const response = await axios.get(`${API_BASE_URL}/api/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(response.data);
      } else {
        // For demo mode, create a mock user
        setUser({
          id: 'demo-user-123',
          email: 'demo@example.com',
          name: 'Demo User',
          picture: 'https://via.placeholder.com/150/4285F4/FFFFFF?text=Demo'
        });
      }
    } catch (error) {
      console.log('Using demo mode');
      // Set demo user even if authentication fails
      setUser({
        id: 'demo-user-123',
        email: 'demo@example.com',
        name: 'Demo User',
        picture: 'https://via.placeholder.com/150/4285F4/FFFFFF?text=Demo'
      });
    } finally {
      setLoading(false);
    }
  };

  const login = (redirectUrl = null) => {
    window.location.href = `${API_BASE_URL}/api/login/google`;
  };

  const logout = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/logout`);
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    login,
    logout,
    checkAuthStatus
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use auth context
const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center">
        <div className="glass-card text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" replace />;
};

// Login Component
const LoginPage = () => {
  const { login, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center">
      <div className="max-w-md w-full mx-4">
        <div className="glass-card text-center">
          <div className="mb-8">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 rounded-2xl shadow-lg mx-auto w-16 h-16 flex items-center justify-center mb-6">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent mb-2">
              Credit Card Manager
            </h1>
            <p className="text-gray-600">
              AI-powered credit optimization & rewards tracking
            </p>
          </div>

          <div className="space-y-6">
            <div className="text-left">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Welcome! Sign in to continue</h2>
              <ul className="text-sm text-gray-600 space-y-2 mb-6">
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Upload PDF credit reports for instant analysis
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Track Chase 5/24 status and eligibility
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Optimize annual fees and credit utilization
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-green-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Get personalized credit insights
                </li>
              </ul>
            </div>

            <button
              onClick={login}
              className="w-full bg-white border border-gray-300 rounded-xl px-6 py-4 flex items-center justify-center space-x-3 hover:bg-gray-50 transition-colors duration-200 shadow-lg hover:shadow-xl"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span className="font-medium text-gray-700">Continue with Google</span>
            </button>

            <p className="text-xs text-gray-500">
              By signing in, you agree to our Terms of Service and Privacy Policy. 
              Your data is encrypted and secure.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component (with authentication)
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [creditCards, setCreditCards] = useState([]);
  const [stats, setStats] = useState({});
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    if (user) {
      fetchCreditCards();
      fetchStats();
    }
  }, [user]);

  const fetchCreditCards = async () => {
    try {
      const token = Cookies.get('access_token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await axios.get(`${API_BASE_URL}/api/credit-cards`, { headers });
      setCreditCards(response.data);
    } catch (error) {
      console.error('Error fetching credit cards:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const token = Cookies.get('access_token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = await axios.get(`${API_BASE_URL}/api/dashboard-stats`, { headers });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    setUploadStatus('Uploading and processing your credit report...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = Cookies.get('access_token');
      const headers = token ? 
        { 'Content-Type': 'multipart/form-data', 'Authorization': `Bearer ${token}` } :
        { 'Content-Type': 'multipart/form-data' };
      
      const response = await axios.post(
        `${API_BASE_URL}/api/upload-credit-report`,
        formData,
        { headers }
      );

      setUploadStatus(`Success! Extracted ${response.data.cards_extracted} credit cards.`);
      await fetchCreditCards();
      await fetchStats();
      
      // Auto switch to cards tab after successful upload
      setTimeout(() => setActiveTab('cards'), 2000);
      
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus(
        error.response?.data?.detail || 'Error processing file. Please try again.'
      );
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false
  });

  const clearAllCards = async () => {
    if (window.confirm('Are you sure you want to clear all credit cards?')) {
      try {
        const token = Cookies.get('access_token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        await axios.delete(`${API_BASE_URL}/api/credit-cards`, { headers });
        await fetchCreditCards();
        await fetchStats();
        setUploadStatus('All credit cards cleared.');
      } catch (error) {
        console.error('Error clearing cards:', error);
      }
    }
  };

  const deleteCard = async (cardId) => {
    if (window.confirm('Are you sure you want to delete this card?')) {
      try {
        const token = Cookies.get('access_token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        await axios.delete(`${API_BASE_URL}/api/credit-cards/${cardId}`, { headers });
        await fetchCreditCards();
        await fetchStats();
      } catch (error) {
        console.error('Error deleting card:', error);
      }
    }
  };

  const formatCurrency = (amount) => {
    if (!amount) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === 'Unknown') return 'Unknown';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const renderIssuerBreakdown = () => {
    const breakdown = stats.issuer_breakdown || {};
    const total = Object.values(breakdown).reduce((sum, count) => sum + count, 0);
    
    if (total === 0) return null;

    return (
      <div className="space-y-3">
        {Object.entries(breakdown).map(([issuer, count]) => {
          const percentage = (count / total) * 100;
          return (
            <div key={issuer} className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">{issuer}</span>
              <div className="flex items-center space-x-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full"
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
                <span className="text-sm text-gray-600 w-8">{count}</span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}
      <header className="glass-card border-0 shadow-xl mb-8">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-3 rounded-2xl shadow-lg">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                  Credit Card Manager
                </h1>
                <p className="text-gray-600 mt-1">Welcome back, {user?.name}!</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <nav className="flex space-x-1 bg-white/50 p-1 rounded-xl backdrop-blur-sm">
                <button
                  onClick={() => setActiveTab('dashboard')}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                    activeTab === 'dashboard'
                      ? 'bg-white shadow-lg text-blue-600'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-white/50'
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                    activeTab === 'upload'
                      ? 'bg-white shadow-lg text-blue-600'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-white/50'
                  }`}
                >
                  Upload Report
                </button>
                <button
                  onClick={() => setActiveTab('cards')}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-200 ${
                    activeTab === 'cards'
                      ? 'bg-white shadow-lg text-blue-600'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-white/50'
                  }`}
                >
                  My Cards ({creditCards.length})
                </button>
              </nav>

              {/* User Menu */}
              <div className="flex items-center space-x-2">
                {user?.picture && (
                  <img 
                    src={user.picture} 
                    alt={user.name}
                    className="w-10 h-10 rounded-full border-2 border-white shadow-lg"
                  />
                )}
                <button
                  onClick={logout}
                  className="px-4 py-2 text-gray-600 hover:text-red-600 transition-colors duration-200"
                  title="Logout"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pb-12">
        
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Credit Portfolio Overview</h2>
              <p className="text-gray-600">Advanced analytics and optimization insights for your credit cards</p>
            </div>
            
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-card hover-lift">
                <div className="flex items-center">
                  <div className="bg-blue-500 p-3 rounded-xl">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Cards</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.total_cards || 0}</p>
                  </div>
                </div>
              </div>

              <div className="glass-card hover-lift">
                <div className="flex items-center">
                  <div className="bg-green-500 p-3 rounded-xl">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Active Cards</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.active_cards || 0}</p>
                  </div>
                </div>
              </div>

              <div className="glass-card hover-lift">
                <div className="flex items-center">
                  <div className="bg-purple-500 p-3 rounded-xl">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Credit Limit</p>
                    <p className="text-2xl font-bold text-gray-900">{formatCurrency(stats.total_credit_limit)}</p>
                  </div>
                </div>
              </div>

              <div className="glass-card hover-lift">
                <div className="flex items-center">
                  <div className="bg-red-500 p-3 rounded-xl">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Utilization</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.credit_utilization || 0}%</p>
                  </div>
                </div>
              </div>
            </div>

            {creditCards.length > 0 && (
              <>
                {/* Advanced Analytics Row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  
                  {/* 5/24 Checker */}
                  <div className="glass-card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Chase 5/24 Status</h3>
                      <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                        stats.five_24_status?.is_eligible 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {stats.five_24_status?.status || 'Unknown'}
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Cards in 24 months</span>
                        <span className="text-2xl font-bold text-gray-900">
                          {stats.five_24_status?.cards_in_24_months || 0}/5
                        </span>
                      </div>
                      
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                          className={`h-3 rounded-full transition-all duration-300 ${
                            (stats.five_24_status?.cards_in_24_months || 0) >= 5 
                              ? 'bg-gradient-to-r from-red-500 to-red-600' 
                              : 'bg-gradient-to-r from-green-500 to-green-600'
                          }`}
                          style={{ width: `${Math.min(((stats.five_24_status?.cards_in_24_months || 0) / 5) * 100, 100)}%` }}
                        ></div>
                      </div>
                      
                      <div className="text-sm text-gray-600">
                        <strong>Remaining slots:</strong> {stats.five_24_status?.remaining_slots || 0}
                      </div>
                      
                      <div className="text-sm text-gray-700 bg-blue-50 p-3 rounded-lg">
                        💡 {stats.five_24_status?.recommendation || 'No recommendation available'}
                      </div>
                    </div>
                  </div>

                  {/* Annual Fees Tracker */}
                  <div className="glass-card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Annual Fees</h3>
                      <div className="bg-orange-100 text-orange-800 px-3 py-1 rounded-full text-sm font-medium">
                        {formatCurrency(stats.total_annual_fees || 0)}
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Fee Cards</span>
                        <span className="font-medium">{stats.portfolio_analysis?.annual_fees?.fee_cards_count || 0}</span>
                      </div>
                      
                      <div className="flex justify-between">
                        <span className="text-gray-600">No-Fee Cards</span>
                        <span className="font-medium">{stats.portfolio_analysis?.annual_fees?.no_fee_cards_count || 0}</span>
                      </div>
                      
                      {stats.portfolio_analysis?.annual_fees?.fee_cards?.length > 0 && (
                        <div className="mt-4">
                          <p className="text-sm font-medium text-gray-700 mb-2">Highest Fee Cards:</p>
                          <div className="space-y-1">
                            {stats.portfolio_analysis.annual_fees.fee_cards
                              .sort((a, b) => b.annual_fee - a.annual_fee)
                              .slice(0, 3)
                              .map((card, index) => (
                              <div key={index} className="flex justify-between text-sm">
                                <span className="text-gray-600 truncate mr-2">{card.card_name}</span>
                                <span className="font-medium">{formatCurrency(card.annual_fee)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Credit Age Analysis */}
                  <div className="glass-card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">Credit Age</h3>
                      <div className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                        {stats.age_analysis?.average_age_years ? `${stats.age_analysis.average_age_years} yrs` : 'N/A'}
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Oldest Card</span>
                        <span className="font-medium text-sm">
                          {stats.age_analysis?.oldest_card_date ? formatDate(stats.age_analysis.oldest_card_date) : 'N/A'}
                        </span>
                      </div>
                      
                      <div className="flex justify-between">
                        <span className="text-gray-600">Newest Card</span>
                        <span className="font-medium text-sm">
                          {stats.age_analysis?.newest_card_date ? formatDate(stats.age_analysis.newest_card_date) : 'N/A'}
                        </span>
                      </div>
                      
                      <div className="flex justify-between">
                        <span className="text-gray-600">Avg Age (months)</span>
                        <span className="font-medium">{stats.age_analysis?.average_age_months || 'N/A'}</span>
                      </div>
                      
                      <div className="text-sm text-gray-700 bg-green-50 p-3 rounded-lg">
                        💡 Longer credit history improves your credit score
                      </div>
                    </div>
                  </div>
                </div>

                {/* Portfolio Insights Row */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Issuer Breakdown */}
                  <div className="glass-card">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Diversification</h3>
                    {renderIssuerBreakdown()}
                    {Object.keys(stats.issuer_breakdown || {}).length > 0 && (
                      <div className="mt-4 text-sm text-gray-700 bg-purple-50 p-3 rounded-lg">
                        💡 You have cards from {Object.keys(stats.issuer_breakdown || {}).length} different issuers
                      </div>
                    )}
                  </div>

                  {/* High Utilization Alerts */}
                  <div className="glass-card">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Utilization Alerts</h3>
                    {stats.top_utilization_cards?.length > 0 ? (
                      <div className="space-y-3">
                        {stats.top_utilization_cards.map((card, index) => (
                          <div key={index} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                            <div>
                              <p className="font-medium text-red-800">{card.card_name}</p>
                              <p className="text-sm text-red-600">{formatCurrency(card.balance)} / {formatCurrency(card.limit)}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-lg font-bold text-red-800">{card.utilization}%</p>
                              <p className="text-xs text-red-600">HIGH</p>
                            </div>
                          </div>
                        ))}
                        <div className="text-sm text-gray-700 bg-yellow-50 p-3 rounded-lg">
                          ⚠️ Consider paying down balances above 30% utilization
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <div className="bg-green-100 w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center">
                          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <p className="text-gray-600">All cards have healthy utilization!</p>
                        <p className="text-sm text-gray-500">Keep utilization below 30% for optimal credit scores</p>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {creditCards.length === 0 && (
              <div className="text-center py-12">
                <div className="bg-gradient-to-r from-blue-400 to-purple-400 w-24 h-24 rounded-full mx-auto mb-6 flex items-center justify-center">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Credit Cards Found</h3>
                <p className="text-gray-600 mb-6">Upload your credit report to unlock advanced analytics and optimization insights</p>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="btn-primary"
                >
                  Upload Credit Report
                </button>
              </div>
            )}
          </div>
        )}

        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Credit Report</h2>
              <p className="text-gray-600">Upload your PDF credit report and let AI extract your credit card information</p>
            </div>

            <div className="glass-card">
              <div 
                {...getRootProps()} 
                className={`upload-zone ${isDragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300'} ${uploading ? 'pointer-events-none opacity-50' : ''}`}
              >
                <input {...getInputProps()} />
                
                <div className="text-center">
                  <div className="bg-gradient-to-r from-blue-400 to-purple-400 w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center">
                    {uploading ? (
                      <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full"></div>
                    ) : (
                      <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    )}
                  </div>
                  
                  {uploading ? (
                    <div>
                      <p className="text-lg font-medium text-gray-900 mb-2">Processing your credit report...</p>
                      <p className="text-gray-600">This may take a moment while AI extracts your credit card data</p>
                    </div>
                  ) : isDragActive ? (
                    <div>
                      <p className="text-lg font-medium text-blue-600 mb-2">Drop your PDF here</p>
                      <p className="text-gray-600">Release to upload and process</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-lg font-medium text-gray-900 mb-2">Drag & drop your credit report PDF</p>
                      <p className="text-gray-600 mb-4">or click to browse files</p>
                      <p className="text-sm text-gray-500">Supports Experian, Credit Karma, and other credit report formats</p>
                    </div>
                  )}
                </div>
              </div>

              {uploadStatus && (
                <div className={`mt-6 p-4 rounded-lg ${uploadStatus.includes('Success') ? 'bg-green-50 text-green-800' : uploadStatus.includes('Error') ? 'bg-red-50 text-red-800' : 'bg-blue-50 text-blue-800'}`}>
                  {uploadStatus}
                </div>
              )}
            </div>

            {creditCards.length > 0 && (
              <div className="mt-8 text-center space-x-4">
                <button
                  onClick={clearAllCards}
                  className="text-red-600 hover:text-red-800 font-medium"
                >
                  Clear All Cards
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={async () => {
                    try {
                      const token = Cookies.get('access_token');
                      const headers = token ? { Authorization: `Bearer ${token}` } : {};
                      await axios.post(`${API_BASE_URL}/api/demo-data`, {}, { headers });
                      await fetchCreditCards();
                      await fetchStats();
                      setUploadStatus('Demo data loaded successfully!');
                    } catch (error) {
                      console.error('Error loading demo data:', error);
                    }
                  }}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Load Demo Data
                </button>
              </div>
            )}

            {creditCards.length === 0 && (
              <div className="mt-8 text-center space-x-4">
                <button
                  onClick={async () => {
                    try {
                      const token = Cookies.get('access_token');
                      const headers = token ? { Authorization: `Bearer ${token}` } : {};
                      await axios.post(`${API_BASE_URL}/api/demo-data`, {}, { headers });
                      await fetchCreditCards();
                      await fetchStats();
                      setUploadStatus('Demo data loaded successfully!');
                    } catch (error) {
                      console.error('Error loading demo data:', error);
                    }
                  }}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Load Demo Data (5 Sample Cards)
                </button>
              </div>
            )}
          </div>
        )}

        {/* Cards Tab */}
        {activeTab === 'cards' && (
          <div>
            <div className="flex justify-between items-center mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">My Credit Cards</h2>
                <p className="text-gray-600 mt-1">Manage and track all your credit cards</p>
              </div>
              {creditCards.length > 0 && (
                <button
                  onClick={() => setActiveTab('upload')}
                  className="btn-primary"
                >
                  Add More Cards
                </button>
              )}
            </div>

            {creditCards.length === 0 ? (
              <div className="text-center py-12">
                <div className="bg-gradient-to-r from-blue-400 to-purple-400 w-24 h-24 rounded-full mx-auto mb-6 flex items-center justify-center">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Credit Cards Found</h3>
                <p className="text-gray-600 mb-6">Upload your credit report to extract your credit card information</p>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="btn-primary"
                >
                  Upload Credit Report
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {creditCards.map((card) => (
                  <div key={card.id} className="credit-card-item group">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center space-x-3">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          card.status === 'Active' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'
                        }`}>
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                          </svg>
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{card.card_name}</h3>
                          <p className="text-sm text-gray-600">{card.issuer}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          card.status === 'Active' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {card.status}
                        </span>
                        <button
                          onClick={() => deleteCard(card.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-800"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Account Number</span>
                        <span className="text-sm font-medium">****{card.account_number}</span>
                      </div>
                      
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Opened</span>
                        <span className="text-sm font-medium">{formatDate(card.open_date)}</span>
                      </div>
                      
                      {card.credit_limit && (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Credit Limit</span>
                          <span className="text-sm font-medium">{formatCurrency(card.credit_limit)}</span>
                        </div>
                      )}
                      
                      {card.current_balance !== null && card.current_balance !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Current Balance</span>
                          <span className="text-sm font-medium">{formatCurrency(card.current_balance)}</span>
                        </div>
                      )}

                      {card.annual_fee !== null && card.annual_fee !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Annual Fee</span>
                          <span className={`text-sm font-medium ${card.annual_fee > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                            {card.annual_fee > 0 ? formatCurrency(card.annual_fee) : 'No Fee'}
                          </span>
                        </div>
                      )}

                      {card.credit_limit && card.current_balance !== null && (
                        <div className="pt-2">
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-600">Utilization</span>
                            <span className="font-medium">{Math.round((card.current_balance / card.credit_limit) * 100)}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full transition-all duration-300 ${
                                (card.current_balance / card.credit_limit) > 0.3 
                                  ? 'bg-gradient-to-r from-red-500 to-red-600' 
                                  : 'bg-gradient-to-r from-blue-500 to-purple-500'
                              }`}
                              style={{ width: `${Math.min((card.current_balance / card.credit_limit) * 100, 100)}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;