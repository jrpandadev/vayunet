'use client';
import { motion, Variants } from 'framer-motion';
import React from 'react';

type TextEffectProps = {
  children: string;
  as?: React.ElementType;
  className?: string;
  per?: 'word' | 'char' | 'line';
  delay?: number;
  variants?: {
    container?: Variants;
    item?: Variants;
  };
};

const defaultContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const defaultItemVariants: Variants = {
  hidden: { opacity: 0, y: 10, filter: 'blur(4px)' },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: { duration: 0.4, ease: 'easeOut' },
  },
};

export function TextEffect({
  children,
  as: Component = 'div',
  className,
  per = 'word',
  delay = 0,
  variants,
}: TextEffectProps) {
  const words = children.split(/(\s+)/);

  const containerVariants = variants?.container || {
    ...defaultContainerVariants,
    visible: {
      ...defaultContainerVariants.visible,
      transition: {
        ...(defaultContainerVariants.visible as any)?.transition,
        delayChildren: delay,
      },
    },
  };

  const itemVariants = variants?.item || defaultItemVariants;

  const MotionComponent = motion[Component as keyof typeof motion] as React.ElementType;

  return (
    <MotionComponent
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className={className}
      aria-label={children}
    >
      {words.map((word, wordIndex) => {
        if (word.match(/^\s+$/)) {
          return <span key={wordIndex}>{word}</span>;
        }
        return (
          <span key={wordIndex} className="inline-block whitespace-nowrap">
            {per === 'char' ? (
              word.split('').map((char, charIndex) => (
                <motion.span
                  key={charIndex}
                  variants={itemVariants}
                  className="inline-block"
                >
                  {char}
                </motion.span>
              ))
            ) : (
              <motion.span variants={itemVariants} className="inline-block">
                {word}
              </motion.span>
            )}
          </span>
        );
      })}
    </MotionComponent>
  );
}
