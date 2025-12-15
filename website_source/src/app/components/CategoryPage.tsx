import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Send, Loader2, CheckCircle2 } from 'lucide-react';
import Navigation from './Navigation';

import { API_BASE } from '../config';


interface Question {
  id: number;
  timestamp: string;
  company: string;
  company_normalized: string;
  question: string;
  question_type: string;
  interview_type: string;

  category: string;
  is_completed: boolean;
}

interface Company {
  name: string;
  count: number;
}

interface CategoryPageProps {
  onLogout: () => void;
}

const categoryNames: Record<string, string> = {
  'product-design': 'Product Design',
  'execution-metrics': 'Execution & Metrics',
  'product-strategy': 'Product Strategy',
  'behavioral': 'Behavioral',
  'estimation-pricing': 'Estimation & Pricing',
  'technical': 'Technical',
  'other': 'Other'
};

const categoryImages: Record<string, string> = {
  'product-design': 'https://images.unsplash.com/photo-1599586108868-9c37eb5172ed?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080',
  'execution-metrics': 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080',
  'product-strategy': 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080',
  'behavioral': 'https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080',
  'estimation-pricing': 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080',
  'technical': 'https://images.unsplash.com/photo-1518770660439-4636190af475?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080',
  'other': 'https://images.unsplash.com/photo-1507925921958-8a62f3d1a50d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&w=1080'
};

export default function CategoryPage({ onLogout }: CategoryPageProps) {
  const { categoryName } = useParams<{ categoryName: string }>();

  // State
  const [questions, setQuestions] = useState<Question[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answer, setAnswer] = useState('');
  const [prompt, setPrompt] = useState('');
  const [feedback, setFeedback] = useState('');
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  // Filters
  const [selectedCompany, setSelectedCompany] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const categoryTitle = categoryNames[categoryName || ''] || categoryName || 'Category';
  const categoryImage = categoryImages[categoryName || ''] || categoryImages['other'];

  // Fetch companies for filter dropdown (category and date specific counts)
  useEffect(() => {
    if (!categoryName) return;

    const params = new URLSearchParams();
    params.append('category', categoryName);
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);

    fetch(`${API_BASE}/companies?${params.toString()}`)
      .then(res => res.json())
      .then(data => setCompanies(data))
      .catch(err => console.error('Error fetching companies:', err));
  }, [categoryName, fromDate, toDate]);

  // Fetch questions when category or filters change
  useEffect(() => {
    if (!categoryName) return;

    setLoading(true);
    const params = new URLSearchParams();
    if (selectedCompany) params.append('company', selectedCompany);
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);

    const url = `${API_BASE}/questions/${categoryName}?${params.toString()}`;

    fetch(url, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
      .then(res => res.json())
      .then(data => {

        const fetchedQuestions = data.questions || [];
        setQuestions(fetchedQuestions);

        // Find index of first uncompleted question
        // Backend sorts: [Completed (Old->New), Uncompleted...]
        // So we just need to find the first one where !is_completed
        const firstUncompletedIndex = fetchedQuestions.findIndex((q: Question) => !q.is_completed);

        // If all are completed, start at 0 (or last). If mix, start at first uncompleted.
        setCurrentQuestionIndex(firstUncompletedIndex >= 0 ? firstUncompletedIndex : 0);

        setAnswer('');
        setFeedback('');
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching questions:', err);
        setLoading(false);
      });
  }, [categoryName, selectedCompany, fromDate, toDate]);

  const currentQuestion = questions[currentQuestionIndex];

  const handleGetFeedback = async () => {
    if (!currentQuestion) return;

    setFeedbackLoading(true);
    try {
      const response = await fetch(`${API_BASE}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentQuestion.question,
          answer: answer,
          prompt: prompt || 'Please analyze my answer and provide feedback.'
        })
      });

      const data = await response.json();
      setFeedback(data.feedback || 'Unable to get feedback.');
    } catch (error) {
      console.error('Error getting feedback:', error);
      setFeedback('Error getting AI feedback. Please try again.');
    } finally {
      setFeedbackLoading(false);
    }
  };

  const handleToggleCompletion = async () => {
    if (!currentQuestion) return;

    // Optimistic update
    const updatedQuestions = [...questions];
    updatedQuestions[currentQuestionIndex] = {
      ...currentQuestion,
      is_completed: !currentQuestion.is_completed
    };
    setQuestions(updatedQuestions);

    try {
      await fetch(`${API_BASE}/questions/${currentQuestion.id}/toggle`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
    } catch (error) {
      console.error('Error toggling completion:', error);
      // Revert on error
      const revertedQuestions = [...questions];
      revertedQuestions[currentQuestionIndex] = currentQuestion;
      setQuestions(revertedQuestions);
    }
  };

  const goToPrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      setAnswer('');
      setFeedback('');
      setPrompt('');
    }
  };

  const goToNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setAnswer('');
      setFeedback('');
      setPrompt('');
    }
  };

  const clearFilters = () => {
    setSelectedCompany('');
    setFromDate('');
    setToDate('');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation onLogout={onLogout} />

      {/* Timeline Image */}
      <div className="relative h-64 bg-gray-900 overflow-hidden">
        <img
          src={categoryImage}
          alt={categoryTitle}
          className="w-full h-full object-cover opacity-70"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900/80 to-transparent"></div>
        <div className="absolute bottom-0 left-0 right-0 p-8">
          <h1 className="text-4xl text-white">{categoryTitle}</h1>
          <p className="text-gray-300 mt-2">
            {loading ? 'Loading...' : `${questions.length} questions available`}
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6">
        <div className="flex gap-6">
          {/* Left Pane - Filters */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm p-6 sticky top-24">
              <h3 className="font-semibold mb-4">Filters</h3>

              {/* Company Filter */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Company</label>
                <select
                  value={selectedCompany}
                  onChange={(e) => setSelectedCompany(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Companies</option>
                  {companies.map((company) => (
                    <option key={company.name} value={company.name}>
                      {company.name} ({company.count})
                    </option>
                  ))}
                </select>
              </div>

              {/* Date Range Filter */}
              {/* Date Range Filter */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">From Date</label>
                <input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">To Date</label>
                <input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {(selectedCompany || fromDate || toDate) && (
                <button
                  onClick={clearFilters}
                  className="w-full px-4 py-2 text-sm text-blue-600 border border-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>

          {/* Middle Pane - Canvas */}
          <div className="flex-1">
            <div className="bg-white rounded-lg shadow-sm">
              {/* Answer Area */}
              <div className="p-6 border-b border-gray-200">
                <h3 className="font-semibold mb-4">Your Answer</h3>
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder=""
                  className="w-full h-80 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              {/* Prompt Input */}
              <div className="p-6">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !feedbackLoading && handleGetFeedback()}
                    placeholder="Ask AI for specific feedback or guidance..."
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleGetFeedback}
                    disabled={feedbackLoading}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {feedbackLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    Get Feedback
                  </button>
                </div>
              </div>

              {/* AI Feedback */}
              {feedback && (
                <div className="p-6 bg-gray-50 border-t border-gray-200">
                  <h3 className="font-semibold mb-4">AI Feedback</h3>
                  <div className="prose max-w-none">
                    <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-white p-4 rounded-lg border border-gray-200">
                      {feedback}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Pane - Question */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm p-6 sticky top-24">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                </div>
              ) : questions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>No questions found for the selected filters.</p>
                  <button
                    onClick={clearFilters}
                    className="mt-4 text-blue-600 hover:underline"
                  >
                    Clear filters
                  </button>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">Question {currentQuestionIndex + 1} of {questions.length}</h3>
                    <button
                      onClick={handleToggleCompletion}
                      className={`p-2 rounded-full transition-colors ${currentQuestion?.is_completed
                        ? 'text-green-600 bg-green-50 hover:bg-green-100'
                        : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
                        }`}
                      title={currentQuestion?.is_completed ? "Mark as incomplete" : "Mark as completed"}
                    >
                      <CheckCircle2 className={`w-6 h-6 ${currentQuestion?.is_completed ? 'fill-green-600 text-white' : ''}`} />
                    </button>
                  </div>

                  {currentQuestion && (
                    <>
                      <div className="mb-4">
                        <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded">
                          {currentQuestion.company_normalized}
                        </span>
                        {currentQuestion.timestamp && (
                          <span className="ml-2 text-xs text-gray-500">
                            {new Date(currentQuestion.timestamp).toLocaleDateString()}
                          </span>
                        )}
                      </div>

                      <div className="mb-6">
                        <p className="text-lg leading-relaxed">
                          {currentQuestion.question}
                        </p>
                      </div>
                    </>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={goToPrevious}
                      disabled={currentQuestionIndex === 0}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </button>
                    <button
                      onClick={goToNext}
                      disabled={currentQuestionIndex === questions.length - 1}
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}