"use client";
import { useEffect, useRef } from "react";
import * as THREE from "three";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

interface Props {
  state: OrbState;
  quality?: "high" | "low";
  className?: string;
}

// ── Constantes visuelles ─────────────────────────────────────────────────────
const N               = 2000;
const MAX_CONNECTIONS  = 6000;
const COL_BASE  = new THREE.Color(0x4ca8e8);
const COL_THINK = new THREE.Color(0x6ec4ff);
const COL_SPEAK = new THREE.Color(0x5ab8f0);
const COL_LISTEN = new THREE.Color(0x00e5ff);

const RADIUS: Record<OrbState, number> = {
  idle:      15,
  listening: 13,
  thinking:   9,
  speaking:  12,
};
const ROT_SPEED: Record<OrbState, number> = {
  idle:      0.003,
  listening: 0.005,
  thinking:  0.010,
  speaking:  0.014,
};
const MAX_DIST: Record<OrbState, number> = {
  idle:      4.5,
  listening: 5.5,
  thinking:  7.0,
  speaking:  6.0,
};

export default function OrbCanvas({ state, quality = "high", className = "" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef  = useRef<OrbState>(state);

  useEffect(() => { stateRef.current = state; }, [state]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // ── Renderer ───────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: quality === "high" });
    renderer.setPixelRatio(quality === "high" ? window.devicePixelRatio : 1);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 1000);
    camera.position.z = 35;

    // ── Particules distribuées sur une sphère ──────────────────────────────
    const positions  = new Float32Array(N * 3);
    const colors     = new Float32Array(N * 3);
    const sizes      = new Float32Array(N);
    const normals: THREE.Vector3[] = [];   // vecteurs unitaires vers la surface

    for (let i = 0; i < N; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);
      const nx    = Math.sin(phi) * Math.cos(theta);
      const ny    = Math.sin(phi) * Math.sin(theta);
      const nz    = Math.cos(phi);
      const r     = RADIUS.idle + (Math.random() - 0.5) * 0.8;

      positions[i * 3]     = nx * r;
      positions[i * 3 + 1] = ny * r;
      positions[i * 3 + 2] = nz * r;
      colors[i * 3]     = COL_BASE.r;
      colors[i * 3 + 1] = COL_BASE.g;
      colors[i * 3 + 2] = COL_BASE.b;
      sizes[i] = Math.random() * 0.35 + 0.08;
      normals.push(new THREE.Vector3(nx, ny, nz));
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color",    new THREE.BufferAttribute(colors, 3));
    geo.setAttribute("size",     new THREE.BufferAttribute(sizes, 1));

    const mat = new THREE.ShaderMaterial({
      vertexShader: `
        attribute float size;
        attribute vec3 color;
        varying vec3 vColor;
        void main() {
          vColor = color;
          vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (280.0 / -mvPos.z);
          gl_Position  = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        void main() {
          float d = length(gl_PointCoord - vec2(0.5));
          if (d > 0.5) discard;
          float alpha = 1.0 - smoothstep(0.28, 0.5, d);
          gl_FragColor = vec4(vColor, alpha * 0.9);
        }
      `,
      transparent: true,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const points = new THREE.Points(geo, mat);
    scene.add(points);

    // ── Lignes de connexion ────────────────────────────────────────────────
    const conGeo = new THREE.BufferGeometry();
    const conPos = new Float32Array(MAX_CONNECTIONS * 6);
    const conCol = new Float32Array(MAX_CONNECTIONS * 6);
    conGeo.setAttribute("position", new THREE.BufferAttribute(conPos, 3));
    conGeo.setAttribute("color",    new THREE.BufferAttribute(conCol, 3));
    const conMat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.15,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const lines = new THREE.LineSegments(conGeo, conMat);
    scene.add(lines);

    // ── Variables d'animation ──────────────────────────────────────────────
    let animId: number;
    let t = 0;
    let currentRadius = RADIUS.idle;
    let currentRotSpeed = ROT_SPEED.idle;

    const resize = () => {
      const w = canvas.clientWidth, h = canvas.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    // ── Boucle principale ──────────────────────────────────────────────────
    function animate() {
      animId = requestAnimationFrame(animate);
      t += 0.016;

      const curState = stateRef.current;
      const targetR = RADIUS[curState];
      currentRadius    += (targetR - currentRadius) * 0.04;
      currentRotSpeed   = currentRotSpeed * 0.95 + ROT_SPEED[curState] * 0.05;

      const posAttr = geo.attributes.position as THREE.BufferAttribute;
      const colAttr = geo.attributes.color    as THREE.BufferAttribute;

      const col = curState === "thinking" ? COL_THINK
                : curState === "speaking"  ? COL_SPEAK
                : curState === "listening" ? COL_LISTEN
                : COL_BASE;

      for (let i = 0; i < N; i++) {
        const n = normals[i];
        let r = currentRadius;

        if (curState === "speaking") {
          // Vortex + respiration
          r += Math.sin(t * 2.2 + i * 0.018) * 1.8;
          const angle = t * 0.6 + i * 0.004;
          const vx = n.x + Math.cos(angle) * 0.025;
          const vy = n.y + Math.sin(angle) * 0.025;
          const vz = n.z;
          const vl = Math.sqrt(vx * vx + vy * vy + vz * vz);
          posAttr.setXYZ(i, (vx / vl) * r, (vy / vl) * r, (vz / vl) * r);
        } else if (curState === "thinking") {
          r += Math.sin(t * 3.5 + i * 0.012) * 0.6;
          posAttr.setXYZ(i, n.x * r, n.y * r, n.z * r);
        } else if (curState === "listening") {
          r += Math.sin(t * 1.8 + i * 0.02) * 0.9;
          posAttr.setXYZ(i, n.x * r, n.y * r, n.z * r);
        } else {
          // idle: respiration lente
          r += Math.sin(t * 0.7 + i * 0.01) * 0.3;
          posAttr.setXYZ(i, n.x * r, n.y * r, n.z * r);
        }

        colAttr.setXYZ(i, col.r, col.g, col.b);
      }
      posAttr.needsUpdate = true;
      colAttr.needsUpdate = true;

      // ── Connexions ───────────────────────────────────────────────────────
      const conPosAttr = conGeo.attributes.position as THREE.BufferAttribute;
      const conColAttr = conGeo.attributes.color    as THREE.BufferAttribute;
      const maxD = MAX_DIST[curState];
      let ci = 0;

      outer: for (let i = 0; i < N; i += 2) {
        const ax = posAttr.getX(i), ay = posAttr.getY(i), az = posAttr.getZ(i);
        for (let j = i + 1; j < N; j += 4) {
          if (ci >= MAX_CONNECTIONS) break outer;
          const bx = posAttr.getX(j), by = posAttr.getY(j), bz = posAttr.getZ(j);
          const dx = ax - bx, dy = ay - by, dz = az - bz;
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (dist < maxD) {
            const alpha = (1 - dist / maxD) * col.r;
            conPosAttr.setXYZ(ci * 2,     ax, ay, az);
            conPosAttr.setXYZ(ci * 2 + 1, bx, by, bz);
            conColAttr.setXYZ(ci * 2,     col.r * alpha, col.g * alpha, col.b * alpha);
            conColAttr.setXYZ(ci * 2 + 1, col.r * alpha, col.g * alpha, col.b * alpha);
            ci++;
          }
        }
      }
      conGeo.setDrawRange(0, ci * 2);
      conPosAttr.needsUpdate = true;
      conColAttr.needsUpdate = true;

      // ── Rotation globale ─────────────────────────────────────────────────
      points.rotation.y += currentRotSpeed;
      lines.rotation.y   = points.rotation.y;

      renderer.render(scene, camera);
    }

    animate();

    return () => {
      cancelAnimationFrame(animId);
      ro.disconnect();
      renderer.dispose();
      geo.dispose();
      mat.dispose();
      conGeo.dispose();
      conMat.dispose();
    };
  }, [quality]);

  return (
    <canvas
      id="orb-canvas"
      ref={canvasRef}
      className={className}
      style={{ width: "100%", height: "100%", pointerEvents: "none" }}
    />
  );
}
