import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

interface CardHeaderProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  return (
    <div
      className={`bg-white border border-[#e2e8f0] rounded-lg shadow-xs overflow-hidden ${className}`}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  className = '',
}) => {
  return (
    <div
      className={`px-5 py-4 border-b border-[#e2e8f0] flex flex-wrap items-center justify-between gap-3 bg-white ${className}`}
    >
      <div>
        {title && (
          <h3 className="text-sm font-bold uppercase tracking-wider text-[#0f172a]">
            {title}
          </h3>
        )}
        {subtitle && (
          <p className="text-xs text-[#64748b] mt-0.5">{subtitle}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};

export const CardContent: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = '',
}) => {
  return <div className={`p-5 ${className}`}>{children}</div>;
};

export const CardFooter: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = '',
}) => {
  return (
    <div
      className={`px-5 py-3 border-t border-[#e2e8f0] bg-slate-50/50 flex items-center justify-between ${className}`}
    >
      {children}
    </div>
  );
};

export default Card;
