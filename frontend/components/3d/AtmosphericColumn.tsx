'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useWebGLSupport } from './useWebGLSupport';
import { SceneFallback } from './SceneFallback';
import { Info, Layers, Wind, Eye } from 'lucide-react';

interface AtmosphericColumnProps {
  windSpeedKmh?: number | null;
  humidityPercent?: number | null;
  temperatureC?: number | null;
  inversionCeilingMeters?: number;
  className?: string;
}

export const AtmosphericColumn: React.FC<AtmosphericColumnProps> = ({
  windSpeedKmh,
  humidityPercent,
  temperatureC,
  inversionCeilingMeters = 850,
  className = '',
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const { supported, prefersReducedMotion } = useWebGLSupport();
  const [activeLayer, setActiveLayer] = useState<string>('Planetary Boundary Layer (PBL)');
  const [isVisible, setIsVisible] = useState<boolean>(true);

  const fallbackLayers = [
    {
      name: 'Free Troposphere',
      altitude: '> 2,000 m',
      status: 'Stable',
      detail: 'Clean regional air mass; high advective wind speeds.'
    },
    {
      name: 'Entrainment Zone / Inversion Cap',
      altitude: `${inversionCeilingMeters} m`,
      status: 'Thermal Inversion',
      detail: 'Prevents vertical dispersion; traps PM2.5 within surface layer.'
    },
    {
      name: 'Planetary Boundary Layer (PBL)',
      altitude: `0 - ${inversionCeilingMeters} m`,
      status: 'High Accumulation',
      detail: 'Active pollutant mixing and transport zone driven by local surface heating.'
    },
    {
      name: 'Surface Canopy / Ground',
      altitude: '0 - 50 m',
      status: 'Emission Source',
      detail: 'Combustion, vehicle exhaust, and industrial fugitive dust.'
    }
  ];

  useEffect(() => {
    if (!supported || prefersReducedMotion || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 400;
    const height = container.clientHeight || 380;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x03111f, 0.035);

    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100);
    camera.position.set(4.5, 3.8, 5.5);
    camera.lookAt(0, 1.6, 0);

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // 3. Vertical Column Grid & Plates
    const gridHelper = new THREE.GridHelper(3.2, 8, 0x00e5ff, 0x0a334a);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Mid-level Inversion Plate (translucent amber/cyan plane)
    const plateGeo = new THREE.PlaneGeometry(3.0, 3.0);
    const plateMat = new THREE.MeshBasicMaterial({
      color: 0xffb52e,
      transparent: true,
      opacity: 0.14,
      side: THREE.DoubleSide,
      wireframe: true,
    });
    const inversionPlate = new THREE.Mesh(plateGeo, plateMat);
    inversionPlate.rotation.x = Math.PI / 2;
    inversionPlate.position.y = 1.6;
    scene.add(inversionPlate);

    // Upper Troposphere Boundary Plate
    const upperPlateMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
      wireframe: true,
    });
    const upperPlate = new THREE.Mesh(plateGeo, upperPlateMat);
    upperPlate.rotation.x = Math.PI / 2;
    upperPlate.position.y = 3.2;
    scene.add(upperPlate);

    // 4. Central Atmospheric Column Wireframe Cage
    const cageGeo = new THREE.CylinderGeometry(1.6, 1.6, 3.4, 16, 4, true);
    const cageMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      wireframe: true,
      transparent: true,
      opacity: 0.12,
    });
    const cage = new THREE.Mesh(cageGeo, cageMat);
    cage.position.y = 1.7;
    scene.add(cage);

    // 5. Particulate & Air Streamlines
    const particleCount = 450;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const velocities = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const baseSpeed = windSpeedKmh ? Math.max(0.005, (windSpeedKmh / 50) * 0.02) : 0.012;

    for (let i = 0; i < particleCount; i++) {
      const x = (Math.random() - 0.5) * 2.6;
      const y = Math.random() * 3.2;
      const z = (Math.random() - 0.5) * 2.6;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      // Trapped pollutants below inversion (y < 1.6) circulate slowly; upper layer advects faster
      velocities[i * 3] = (baseSpeed * (0.8 + Math.random() * 0.5));
      velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.004;
      velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.004;

      if (y < 1.6) {
        // High concentration near surface: amber-red tint
        colors[i * 3] = 1.0;
        colors[i * 3 + 1] = 0.55;
        colors[i * 3 + 2] = 0.15;
      } else {
        // Dispersed clean upper air: cyan tint
        colors[i * 3] = 0.0;
        colors[i * 3 + 1] = 0.9;
        colors[i * 3 + 2] = 1.0;
      }
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.045,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
    });

    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // 6. Animation & Lifecycle Loop
    let animId: number;
    let clock = new THREE.Clock();

    const render = () => {
      animId = requestAnimationFrame(render);

      const delta = clock.getDelta();
      const pos = particleGeo.attributes.position.array as Float32Array;

      for (let i = 0; i < particleCount; i++) {
        // Move along x (wind vector)
        pos[i * 3] += velocities[i * 3];
        pos[i * 3 + 1] += velocities[i * 3 + 1];
        pos[i * 3 + 2] += velocities[i * 3 + 2];

        // Boundary wrap
        if (pos[i * 3] > 1.4) pos[i * 3] = -1.4;
        if (pos[i * 3 + 1] > 3.2) pos[i * 3 + 1] = 0.05;
        if (pos[i * 3 + 1] < 0) pos[i * 3 + 1] = 3.15;
      }
      particleGeo.attributes.position.needsUpdate = true;

      // Gentle orbital oscillation
      cage.rotation.y += 0.0025;
      gridHelper.rotation.y += 0.0008;

      renderer.render(scene, camera);
    };

    render();

    // 7. Resize Observer
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // 8. Intersection Observer (pause when offscreen)
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
        if (!entry.isIntersecting) {
          cancelAnimationFrame(animId);
        } else {
          render();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(container);

    // Clean up
    return () => {
      cancelAnimationFrame(animId);
      observer.disconnect();
      resizeObserver.disconnect();

      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      gridHelper.geometry.dispose();
      if (Array.isArray(gridHelper.material)) {
        gridHelper.material.forEach((m) => m.dispose());
      } else {
        gridHelper.material.dispose();
      }
      particleGeo.dispose();
      particleMat.dispose();
      plateGeo.dispose();
      plateMat.dispose();
      upperPlateMat.dispose();
      cageGeo.dispose();
      cageMat.dispose();
      renderer.dispose();
    };
  }, [supported, prefersReducedMotion, windSpeedKmh, inversionCeilingMeters]);

  if (!supported || prefersReducedMotion) {
    return (
      <SceneFallback
        title="Vertical Atmospheric Stratification"
        description="Conceptual model illustrating planetary boundary layer compression and inversion ceiling dynamics over Delhi NCR."
        layers={fallbackLayers}
        reason={prefersReducedMotion ? 'reduced-motion' : 'unsupported'}
      />
    );
  }

  return (
    <div
      role="region"
      aria-label="3D Atmospheric Stratification Model"
      className={`relative w-full h-[380px] bg-[#061827] border border-[rgba(0,213,255,0.14)] rounded-xl overflow-hidden shadow-2xl shadow-black/40 flex flex-col ${className}`}
    >
      {/* Top HUD Overlay */}
      <div className="absolute top-3 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-[#00E5FF]" />
          <span className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
            Atmospheric Column & Mixing Layer
          </span>
        </div>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[rgba(255,181,46,0.10)] text-[#FFB52E] border border-[rgba(255,181,46,0.25)]">
          Conceptual Atmospheric Visualization
        </span>
      </div>

      {/* WebGL Canvas Mount */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Bottom Layer Annotations HUD */}
      <div className="absolute bottom-3 left-4 right-4 z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none text-[11px] font-mono">
        <div className="flex items-center gap-3 bg-[rgba(3,17,31,0.85)] backdrop-blur-md px-3 py-1.5 rounded border border-[rgba(0,213,255,0.12)]">
          <span className="text-[#00E5FF]">Alt: 0–2,000m</span>
          <span className="text-[#2E5470]">|</span>
          <span className="text-[#FFB52E]">Inversion Cap: ~{inversionCeilingMeters}m</span>
          <span className="text-[#2E5470]">|</span>
          <span className="text-[#27E0C3]">
            Surface Wind: {windSpeedKmh != null ? `${windSpeedKmh} km/h` : 'TELEMETRY UNAVAILABLE'}
          </span>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 text-[#7BA4BC] bg-[rgba(3,17,31,0.85)] px-2.5 py-1.5 rounded border border-[rgba(0,213,255,0.10)]">
          <Info className="w-3 h-3 text-[#00E5FF]" />
          <span>Lower dense particle layer shows thermal trap</span>
        </div>
      </div>

      {/* Accessibility Screen Reader Text */}
      <div className="sr-only">
        Conceptual 3D visualization demonstrating the vertical structure of the atmosphere from the ground up to 2,000 meters. The model highlights a thermal inversion layer at approximately {inversionCeilingMeters} meters where air temperature inversion restricts vertical dispersion, trapping particulate matter in the planetary boundary layer.
      </div>
    </div>
  );
};

export default AtmosphericColumn;
