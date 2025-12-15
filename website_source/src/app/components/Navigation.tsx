import { useNavigate, useLocation } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import Logo from './Logo';

const navItems = [
  { name: 'About', path: '/about' },
  { name: 'Product Design', path: '/category/product-design' },
  { name: 'Execution & Metrics', path: '/category/execution-metrics' },
  { name: 'Product Strategy', path: '/category/product-strategy' },
  { name: 'Behavioral', path: '/category/behavioral' },
  { name: 'Estimation & Pricing', path: '/category/estimation-pricing' },
  { name: 'Technical', path: '/category/technical' },
  { name: 'Other', path: '/category/other' },
];

interface NavigationProps {
  onLogout: () => void;
}

export default function Navigation({ onLogout }: NavigationProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <button onClick={() => navigate('/about')} className="flex items-center">
            <Logo />
          </button>

          <div className="hidden lg:flex items-center gap-8">
            {navItems.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`text-xs font-medium transition-colors ${location.pathname === item.path
                  ? 'text-blue-600'
                  : 'text-gray-700 hover:text-gray-900'
                  }`}
              >
                {item.name}
              </button>
            ))}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-xs font-medium text-gray-700 hover:text-red-600 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}