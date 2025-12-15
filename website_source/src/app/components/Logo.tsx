import { GraduationCap } from 'lucide-react';

interface LogoProps {
  className?: string;
}

export default function Logo({ className = '' }: LogoProps) {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
        <GraduationCap className="w-5 h-5 text-white" />
      </div>
      <span className="text-xl">Product Siksha</span>
    </div>
  );
}
