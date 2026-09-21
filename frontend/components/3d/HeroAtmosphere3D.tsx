'use client';

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useWebGLSupport } from './useWebGLSupport';

export const HeroAtmosphere3D: React.FC<{ className?: string }> = ({ className = '' }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const { supported, prefersReducedMotion } = useWebGLSupport();

  useEffect(() => {
    if (!supported || prefersReducedMotion || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 450;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x03111f, 0.05);

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 50);
    camera.position.set(0, 0, 7);

    const renderer = new THREE.WebGLRenderer({
      antialias: false, // keep lightweight
      alpha: true,
      powerPreference: 'low-power',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // Subtle atmospheric flow particles (only 220 particles to minimize GPU work)
    const particleCount = 220;
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(particleCount * 3);
    const vels = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 14;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 8;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 6;

      vels[i * 3] = 0.006 + Math.random() * 0.008; // slow horizontal wind drift
      vels[i * 3 + 1] = (Math.random() - 0.5) * 0.002;
      vels[i * 3 + 2] = (Math.random() - 0.5) * 0.002;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));

    const mat = new THREE.PointsMaterial({
      color: 0x00e5ff,
      size: 0.06,
      transparent: true,
      opacity: 0.45,
    });

    const particles = new THREE.Points(geo, mat);
    scene.add(particles);

    let animId: number;
    const render = () => {
      animId = requestAnimationFrame(render);

      const positions = geo.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        positions[i * 3] += vels[i * 3];
        positions[i * 3 + 1] += vels[i * 3 + 1];

        // Wrap around
        if (positions[i * 3] > 7) {
          positions[i * 3] = -7;
        }
      }
      geo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    render();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) {
        cancelAnimationFrame(animId);
      } else {
        render();
      }
    });
    observer.observe(container);

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      observer.disconnect();

      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      geo.dispose();
      mat.dispose();
      renderer.dispose();
    };
  }, [supported, prefersReducedMotion]);

  if (!supported || prefersReducedMotion) {
    return null; // Silent graceful degrade on low capability
  }

  return (
    <div
      aria-hidden="true"
      className={`absolute inset-0 pointer-events-none overflow-hidden z-0 ${className}`}
    >
      <div ref={mountRef} className="w-full h-full opacity-60" />
    </div>
  );
};

export default HeroAtmosphere3D;
