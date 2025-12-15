import { useNavigate } from 'react-router-dom';
import { GraduationCap, Target, Users } from 'lucide-react';
import Navigation from './Navigation';
import Logo from './Logo';

const categories = [
  { name: 'Product Design', path: 'product-design' },
  { name: 'Execution & Metrics', path: 'execution-metrics' },
  { name: 'Product Strategy', path: 'product-strategy' },
  { name: 'Behavioral', path: 'behavioral' },
  { name: 'Estimation & Pricing', path: 'estimation-pricing' },
  { name: 'Technical', path: 'technical' },
  { name: 'Other', path: 'other' },
];

interface AboutPageProps {
  onLogout: () => void;
}

export default function AboutPage({ onLogout }: AboutPageProps) {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      <Navigation onLogout={onLogout} />

      {/* Hero Section - Apple Style */}
      <section className="pt-20 pb-24 px-6 text-center bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-6xl mb-6 tracking-tight">Product Siksha</h1>
          <p className="text-2xl text-gray-600 max-w-3xl mx-auto">
            Master product management interviews with AI-powered feedback and comprehensive practice.
          </p>
        </div>
      </section>

      {/* Story Section */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4 mb-8">
            <GraduationCap className="w-12 h-12 text-blue-600" />
            <h2 className="text-4xl">Our Story</h2>
          </div>
          <div className="space-y-6 text-lg text-gray-700 leading-relaxed">
            <p>
              Product Siksha was born from a simple observation: aspiring product managers needed
              a better way to prepare for interviews. Traditional resources were scattered, feedback
              was limited, and practice opportunities were few.
            </p>
            <p>
              We envisioned a platform where candidates could practice real PM interview questions,
              receive instant AI-powered feedback, and track their progress across all major interview
              categories. A place where preparation meets perfection.
            </p>
            <p>
              Today, Product Siksha serves thousands of aspiring product managers, helping them land
              their dream roles at top tech companies around the world.
            </p>
          </div>
        </div>
      </section>

      {/* Vision Section */}
      <section className="py-20 px-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4 mb-8">
            <Target className="w-12 h-12 text-blue-600" />
            <h2 className="text-4xl">Our Vision</h2>
          </div>
          <div className="space-y-6 text-lg text-gray-700 leading-relaxed">
            <p>
              We believe that every aspiring product manager deserves access to world-class interview
              preparation. Our vision is to democratize PM education and make expert-level training
              accessible to everyone, regardless of their background or location.
            </p>
            <p>
              Through advanced AI technology and carefully curated content, we're building the most
              comprehensive platform for PM interview success. We're not just helping people pass
              interviews—we're helping them become better product thinkers.
            </p>
          </div>
        </div>
      </section>

      {/* Leadership Section */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-4 mb-12">
            <Users className="w-12 h-12 text-blue-600" />
            <h2 className="text-4xl">Leadership</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-32 h-32 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4"></div>
              <h3 className="text-xl mb-2">Sarah Chen</h3>
              <p className="text-gray-600 mb-2">Founder & CEO</p>
              <p className="text-sm text-gray-500">Ex-Google PM, Stanford MBA</p>
            </div>
            <div className="text-center">
              <div className="w-32 h-32 bg-gradient-to-br from-green-500 to-blue-600 rounded-full mx-auto mb-4"></div>
              <h3 className="text-xl mb-2">Michael Rodriguez</h3>
              <p className="text-gray-600 mb-2">Chief Product Officer</p>
              <p className="text-sm text-gray-500">Ex-Meta PM, MIT</p>
            </div>
            <div className="text-center">
              <div className="w-32 h-32 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full mx-auto mb-4"></div>
              <h3 className="text-xl mb-2">Priya Sharma</h3>
              <p className="text-gray-600 mb-2">Head of AI</p>
              <p className="text-sm text-gray-500">Ex-Amazon ML, Carnegie Mellon</p>
            </div>
          </div>
        </div>
      </section>

      {/* Categories Section */}
      <section className="py-20 px-6 bg-gray-900 text-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl mb-12 text-center">Practice Categories</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {categories.map((category) => (
              <button
                key={category.path}
                onClick={() => navigate(`/category/${category.path}`)}
                className="bg-white/10 hover:bg-white/20 backdrop-blur-sm p-8 rounded-2xl transition-all text-left"
              >
                <h3 className="text-xl mb-2">{category.name}</h3>
                <p className="text-gray-400 text-sm">
                  Practice and get AI feedback
                </p>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 bg-black text-white text-center">
        <Logo className="mx-auto mb-4" />
        <p className="text-gray-400">© 2024 Product Siksha. All rights reserved.</p>
      </footer>
    </div>
  );
}