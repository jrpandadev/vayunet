'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useWebGLSupport } from './useWebGLSupport';
import { SceneFallback } from './SceneFallback';
import { Orbit, Activity, ShieldCheck, Cpu } from 'lucide-react';

export const MethodologyPipeline3D: React.FC<{ className?: string }> = ({ className = '' }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const { supported, prefersReducedMotion } = useWebGLSupport();
  const [activeStage, setActiveStage] = useState<string>('Fusion & Coupled Assimilation');

  const fallbackStages = [
    {
      name: '1. Multimodal Observation Grid',
      altitude: 'Orbit + Surface',
      status: 'Continuous',
      detail: 'Sentinel-5P TROPOMI orbiters + CPCB CAAQMS certified ground nodes.'
    },
    {
      name: '2. Atmospheric Coupling Layer',
      altitude: '0 - 3,000 m',
      status: 'Synoptic',
      detail: 'Wind vector advection and planetary boundary layer inversion dynamics.'
    },
    {
      name: '3. Deterministic AI / ML Pipeline',
      altitude: 'Analytical',
      status: 'Active',
      detail: 'XGBoost 72h predictive forecasting + Gemini multimodal vision validation.'
    },
    {
      name: '4. Civic & Authority Dispatch',
      altitude: 'Enforcement',
      status: 'Actionable',
      detail: 'Corroborated incident dossiers routed to environmental enforcement units.'
    }
  ];

  useEffect(() => {
    if (!supported || prefersReducedMotion || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 360;

    // Scene & Camera
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x03111f, 0.04);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 3.2, 6.2);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // 1. Orbital Ring (Satellite Observation Tier)
    const orbitCurve = new THREE.EllipseCurve(0, 0, 3.4, 1.4, 0, 2 * Math.PI, false, 0);
    const orbitPoints = orbitCurve.getPoints(64);
    const orbitGeo = new THREE.BufferGeometry().setFromPoints(
      orbitPoints.map((p) => new THREE.Vector3(p.x, 2.2, p.y))
    );
    const orbitMat = new THREE.LineDashedMaterial({
      color: 0x00e5ff,
      dashSize: 0.15,
      gapSize: 0.08,
      transparent: true,
      opacity: 0.45,
    });
    const orbitLine = new THREE.Line(orbitGeo, orbitMat);
    orbitLine.computeLineDistances();
    scene.add(orbitLine);

    // Satellite Probe Marker
    const satGeo = new THREE.BoxGeometry(0.18, 0.18, 0.28);
    const satMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
    const satelliteMesh = new THREE.Mesh(satGeo, satMat);
    scene.add(satelliteMesh);

    // 2. Ground Sensor Grid (Base Tier)
    const groundGrid = new THREE.GridHelper(4.8, 12, 0x00e5ff, 0x0a2638);
    groundGrid.position.y = -0.6;
    scene.add(groundGrid);

    // 3. Central AI Neural Convergence Sphere
    const coreGeo = new THREE.IcosahedronGeometry(0.55, 1);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x27e0c3,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.position.set(0, 0.6, 0);
    scene.add(coreMesh);

    // Inner glowing kernel
    const kernelGeo = new THREE.SphereGeometry(0.24, 16, 16);
    const kernelMat = new THREE.MeshBasicMaterial({
      color: 0x00e5ff,
      transparent: true,
      opacity: 0.9,
    });
    const kernelMesh = new THREE.Mesh(kernelGeo, kernelMat);
    kernelMesh.position.set(0, 0.6, 0);
    scene.add(kernelMesh);

    // 4. Ingesting Streamlines (Flowing into Core)
    const streamCount = 180;
    const streamGeo = new THREE.BufferGeometry();
    const streamPos = new Float32Array(streamCount * 3);
    const streamVels = new Float32Array(streamCount * 3);

    for (let i = 0; i < streamCount; i++) {
      // Streamlines originate from outer perimeter and converge on center (0, 0.6, 0)
      const angle = Math.random() * Math.PI * 2;
      const radius = 1.8 + Math.random() * 1.5;
      const yOrigin = (Math.random() - 0.2) * 2.0;

      streamPos[i * 3] = Math.cos(angle) * radius;
      streamPos[i * 3 + 1] = yOrigin;
      streamPos[i * 3 + 2] = Math.sin(angle) * radius;

      // Convergence direction vector
      streamVels[i * 3] = -Math.cos(angle) * 0.015;
      streamVels[i * 3 + 1] = (0.6 - yOrigin) * 0.008;
      streamVels[i * 3 + 2] = -Math.sin(angle) * 0.015;
    }

    streamGeo.setAttribute('position', new THREE.BufferAttribute(streamPos, 3));
    const streamMat = new THREE.PointsMaterial({
      color: 0x00e5ff,
      size: 0.04,
      transparent: true,
      opacity: 0.8,
    });
    const streamPoints = new THREE.Points(streamGeo, streamMat);
    scene.add(streamPoints);

    // Animation Loop
    let animId: number;
    let clock = new THREE.Clock();

    const render = () => {
      animId = requestAnimationFrame(render);
      const elapsed = clock.getElapsedTime();

      // Rotate Satellite along orbit
      satelliteMesh.position.x = Math.cos(elapsed * 0.7) * 3.4;
      satelliteMesh.position.z = Math.sin(elapsed * 0.7) * 1.4;
      satelliteMesh.position.y = 2.2;
      satelliteMesh.rotation.y = elapsed * 0.8;

      // Pulse Central AI Core
      coreMesh.rotation.y = elapsed * 0.4;
      coreMesh.rotation.x = elapsed * 0.2;
      const scale = 1 + Math.sin(elapsed * 2.5) * 0.06;
      coreMesh.scale.set(scale, scale, scale);

      // Advance converging streamlines
      const pos = streamGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < streamCount; i++) {
        pos[i * 3] += streamVels[i * 3];
        pos[i * 3 + 1] += streamVels[i * 3 + 1];
        pos[i * 3 + 2] += streamVels[i * 3 + 2];

        // Reset if near core
        const dist = Math.hypot(pos[i * 3], pos[i * 3 + 1] - 0.6, pos[i * 3 + 2]);
        if (dist < 0.25) {
          const angle = Math.random() * Math.PI * 2;
          const radius = 2.2 + Math.random() * 1.0;
          const yOrigin = (Math.random() - 0.2) * 2.0;

          pos[i * 3] = Math.cos(angle) * radius;
          pos[i * 3 + 1] = yOrigin;
          pos[i * 3 + 2] = Math.sin(angle) * radius;
        }
      }
      streamGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    render();

    // Resize
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

    // Visibility
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

      orbitGeo.dispose();
      orbitMat.dispose();
      satGeo.dispose();
      satMat.dispose();
      groundGrid.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      kernelGeo.dispose();
      kernelMat.dispose();
      streamGeo.dispose();
      streamMat.dispose();
      renderer.dispose();
    };
  }, [supported, prefersReducedMotion]);

  if (!supported || prefersReducedMotion) {
    return (
      <SceneFallback
        title="Federated Intelligence Assimilation Architecture"
        description="Conceptual schematic detailing the convergence of orbital observation, meteorological dynamics, ground truth sensors, and AI reasoning."
        layers={fallbackStages}
        reason={prefersReducedMotion ? 'reduced-motion' : 'unsupported'}
      />
    );
  }

  return (
    <div
      role="region"
      aria-label="3D Environmental Intelligence Pipeline Schematic"
      className={`relative w-full h-[360px] bg-[#061827] border border-[rgba(0,213,255,0.14)] rounded-xl overflow-hidden shadow-2xl shadow-black/40 flex flex-col ${className}`}
    >
      {/* Top HUD */}
      <div className="absolute top-3 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[#27E0C3]" />
          <span className="text-xs font-bold uppercase tracking-wider text-[#E8F4FD]">
            Coupled Assimilation & Reasoning Core
          </span>
        </div>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[rgba(0,213,255,0.08)] text-[#00E5FF] border border-[rgba(0,213,255,0.20)]">
          Illustrative — Conceptual Architecture Model
        </span>
      </div>

      {/* WebGL Canvas */}
      <div ref={mountRef} className="w-full h-full" />

      {/* Interactive Legend Overlay */}
      <div className="absolute bottom-3 left-4 right-4 z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none text-[11px] font-mono">
        <div className="flex items-center gap-3 bg-[rgba(3,17,31,0.85)] backdrop-blur-md px-3 py-1.5 rounded border border-[rgba(0,213,255,0.12)]">
          <span className="flex items-center gap-1.5 text-[#00E5FF]">
            <span className="w-2 h-2 rounded-full bg-[#00E5FF] inline-block animate-pulse" />
            Orbital Sentinel-5P
          </span>
          <span className="text-[#2E5470]">→</span>
          <span className="flex items-center gap-1.5 text-[#27E0C3]">
            <span className="w-2 h-2 rounded-full bg-[#27E0C3] inline-block" />
            Gemini Multimodal Core
          </span>
          <span className="text-[#2E5470]">→</span>
          <span className="text-[#E8F4FD]">
            Ground Sensor Baseline
          </span>
        </div>

        <span className="hidden sm:inline-block text-[#7BA4BC] text-[10px] bg-[rgba(3,17,31,0.85)] px-2 py-1 rounded border border-[rgba(0,213,255,0.10)]">
          Zero-Lag Local WebGL Lifecycle
        </span>
      </div>

      <div className="sr-only">
        Interactive 3D conceptual diagram showing the four tiers of data fusion: orbital satellite sweeps, synoptic atmospheric wind vectors, ground CAAQMS sensor grids, and multimodal AI cross-validation.
      </div>
    </div>
  );
};

export default MethodologyPipeline3D;
