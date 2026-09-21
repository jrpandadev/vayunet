'use client';
import React, { useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

type TransitionPanelProps = {
  children: React.ReactNode;
  activeIndex: number;
  className?: string;
};

export function TransitionPanel({
  children,
  activeIndex,
  className,
}: TransitionPanelProps) {
  const previousIndex = useRef(activeIndex);
  const direction = activeIndex > previousIndex.current ? 1 : -1;
  previousIndex.current = activeIndex;

  const childArray = React.Children.toArray(children);

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 20 : -20,
      opacity: 0,
      filter: 'blur(4px)',
    }),
    center: {
      x: 0,
      opacity: 1,
      filter: 'blur(0px)',
    },
    exit: (direction: number) => ({
      x: direction < 0 ? 20 : -20,
      opacity: 0,
      filter: 'blur(4px)',
    }),
  };

  return (
    <div className={`relative overflow-hidden ${className || ''}`}>
      <AnimatePresence initial={false} custom={direction} mode="popLayout">
        <motion.div
          key={activeIndex}
          custom={direction}
          variants={variants}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{
            x: { type: 'spring', stiffness: 300, damping: 30 },
            opacity: { duration: 0.2 },
            filter: { duration: 0.2 },
          }}
          className="w-full"
        >
          {childArray[activeIndex]}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
