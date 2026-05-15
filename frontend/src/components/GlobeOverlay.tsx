"use client";
import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";
import * as THREE from "three";
// @ts-ignore — OrbitControls n'a pas de types dans le package three bundled
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export interface GlobeAction {
  globe_action: "show_earth" | "fly_to" | "route" | "my_location" | "hide";
  lat?:       number;
  lon?:       number;
  from_lat?:  number;
  from_lon?:  number;
  from_name?: string;
  to_lat?:    number;
  to_lon?:    number;
  to_name?:   string;
  target?:    string;
}

export interface GlobeHandle {
  dispatch: (action: GlobeAction) => void;
}

const EARTH_RADIUS = 100;

const TEXTURES = {
  day:    "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
  bump:   "https://unpkg.com/three-globe/example/img/earth-topology.png",
  clouds: "https://unpkg.com/three-globe/example/img/earth-clouds.png",
};

function latLonToVec3(lat: number, lon: number, radius: number) {
  const phi   = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -(radius * Math.sin(phi) * Math.cos(theta)),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta),
  );
}

const GlobeOverlay = forwardRef<GlobeHandle, { isOpen: boolean; onClose: () => void }>(
  ({ isOpen, onClose }, ref) => {
    const canvasRef   = useRef<HTMLCanvasElement>(null);
    const targetRef   = useRef<HTMLDivElement>(null);
    const coordsRef   = useRef<HTMLDivElement>(null);
    const sceneRef    = useRef<{
      renderer: THREE.WebGLRenderer;
      scene:    THREE.Scene;
      camera:   THREE.PerspectiveCamera;
      controls: InstanceType<typeof OrbitControls>;
      clouds:   THREE.Mesh;
      stars:    THREE.Points;
      scanLine: THREE.Mesh;
      markers:  THREE.Group;
      routes:   THREE.Group;
      animId:   number;
      flight:   { lat: number; lon: number; dist: number } | null;
    } | null>(null);

    // ── Init Three.js ────────────────────────────────────────────────────────
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas || sceneRef.current) return;

      const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.setSize(window.innerWidth, window.innerHeight);

      const scene  = new THREE.Scene();
      scene.background = new THREE.Color(0x000000);

      const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 2000);
      camera.position.z = 400;

      // Lumières
      scene.add(new THREE.AmbientLight(0xffffff, 0.4));
      const sun = new THREE.DirectionalLight(0xffffff, 1.2);
      sun.position.set(5, 3, 5);
      scene.add(sun);

      // Étoiles
      const starVerts: number[] = [];
      for (let i = 0; i < 5000; i++) {
        starVerts.push(
          (Math.random() - 0.5) * 2000,
          (Math.random() - 0.5) * 2000,
          (Math.random() - 0.5) * 2000,
        );
      }
      const starGeo = new THREE.BufferGeometry();
      starGeo.setAttribute("position", new THREE.Float32BufferAttribute(starVerts, 3));
      const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.7, transparent: true, opacity: 0.8 }));
      scene.add(stars);

      // Terre
      const loader  = new THREE.TextureLoader();
      const earthMat = new THREE.MeshStandardMaterial({
        map:      loader.load(TEXTURES.day),
        bumpMap:  loader.load(TEXTURES.bump),
        bumpScale: 2,
        metalness: 0.1,
        roughness: 0.8,
      });
      scene.add(new THREE.Mesh(new THREE.SphereGeometry(EARTH_RADIUS, 64, 64), earthMat));

      // Nuages
      const clouds = new THREE.Mesh(
        new THREE.SphereGeometry(EARTH_RADIUS + 2, 64, 64),
        new THREE.MeshStandardMaterial({ map: loader.load(TEXTURES.clouds), transparent: true, opacity: 0.4, depthWrite: false }),
      );
      scene.add(clouds);

      // Atmosphère (shader fresnel cyan)
      const atmosphere = new THREE.Mesh(
        new THREE.SphereGeometry(EARTH_RADIUS * 1.15, 64, 64),
        new THREE.ShaderMaterial({
          vertexShader: `
            varying vec3 vNormal;
            void main() {
              vNormal = normalize(normalMatrix * normal);
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `,
          fragmentShader: `
            varying vec3 vNormal;
            void main() {
              float i = pow(0.7 - dot(vNormal, vec3(0,0,1)), 3.0);
              gl_FragColor = vec4(0.0, 0.9, 1.0, 1.0) * i;
            }
          `,
          side: THREE.BackSide,
          blending: THREE.AdditiveBlending,
          transparent: true,
        }),
      );
      scene.add(atmosphere);

      // Ligne de scan holographique
      const scanLine = new THREE.Mesh(
        new THREE.RingGeometry(EARTH_RADIUS * 1.02, EARTH_RADIUS * 1.03, 64),
        new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.3, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }),
      );
      scanLine.rotation.x = Math.PI / 2;
      scene.add(scanLine);

      // Groupes markers / routes
      const markers = new THREE.Group();
      const routes  = new THREE.Group();
      scene.add(markers, routes);

      // OrbitControls
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping   = true;
      controls.dampingFactor   = 0.05;
      controls.rotateSpeed     = 0.5;
      controls.zoomSpeed       = 0.5;
      controls.minDistance     = 160;
      controls.maxDistance     = 600;
      controls.autoRotate      = true;
      controls.autoRotateSpeed = 0.5;

      // Resize
      const onResize = () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      };
      window.addEventListener("resize", onResize);

      let animId = 0;
      const state = { renderer, scene, camera, controls, clouds, stars, scanLine, markers, routes, animId, flight: null as typeof sceneRef.current extends null ? never : NonNullable<typeof sceneRef.current>["flight"] };
      sceneRef.current = state;

      function animate() {
        const s = sceneRef.current;
        if (!s) return;
        s.animId = requestAnimationFrame(animate);
        s.controls.update();
        s.clouds.rotation.y    += 0.0002;
        s.stars.rotation.y     += 0.00008;
        const time = Date.now() * 0.001;
        (s.scanLine.material as THREE.MeshBasicMaterial).opacity = 0.2 + Math.abs(Math.sin(time)) * 0.2;
        s.scanLine.position.y  = Math.sin(time * 0.5) * (EARTH_RADIUS * 0.8);

        if (s.flight) {
          const tp = latLonToVec3(s.flight.lat, s.flight.lon, s.flight.dist);
          const tl = latLonToVec3(s.flight.lat, s.flight.lon, EARTH_RADIUS);
          s.camera.position.lerp(tp, 0.05);
          s.controls.target.lerp(tl, 0.05);
          if (s.camera.position.distanceTo(tp) < 1) s.flight = null;
        }

        s.renderer.render(s.scene, s.camera);
      }
      animate();

      return () => {
        if (sceneRef.current) cancelAnimationFrame(sceneRef.current.animId);
        window.removeEventListener("resize", onResize);
        renderer.dispose();
        sceneRef.current = null;
      };
    }, []);

    // ── API publique via ref ─────────────────────────────────────────────────
    useImperativeHandle(ref, () => ({
      dispatch(action: GlobeAction) {
        const s = sceneRef.current;
        if (!s) return;

        const clearGroups = () => {
          while (s.markers.children.length) s.markers.remove(s.markers.children[0]);
          while (s.routes.children.length)  s.routes.remove(s.routes.children[0]);
        };

        const addMarker = (lat: number, lon: number, color = "#00e5ff") => {
          const pos = latLonToVec3(lat, lon, EARTH_RADIUS);
          const c   = new THREE.Color(color);
          const ring = new THREE.Mesh(
            new THREE.RingGeometry(2, 3, 32),
            new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide, transparent: true, opacity: 0.6 }),
          );
          ring.position.copy(pos);
          ring.lookAt(new THREE.Vector3(0, 0, 0));
          s.markers.add(ring);
          const dot = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 16), new THREE.MeshBasicMaterial({ color: c }));
          dot.position.copy(pos);
          s.markers.add(dot);
        };

        switch (action.globe_action) {
          case "show_earth":
            if (targetRef.current) targetRef.current.textContent = "GLOBE TERRESTRE";
            if (coordsRef.current) coordsRef.current.textContent = "";
            s.controls.autoRotate = true;
            break;

          case "fly_to": {
            const lt = action.lat ?? 0, ln = action.lon ?? 0;
            clearGroups();
            addMarker(lt, ln);
            s.controls.autoRotate = false;
            s.flight = { lat: lt, lon: ln, dist: 280 };
            if (targetRef.current) targetRef.current.textContent = `⊕ ${(action.target ?? "").toUpperCase()}`;
            if (coordsRef.current) coordsRef.current.textContent = `LAT ${lt.toFixed(4)}°  LON ${ln.toFixed(4)}°`;
            break;
          }

          case "route": {
            clearGroups();
            if (action.from_lat != null) addMarker(action.from_lat, action.from_lon ?? 0, "#00e5ff");
            if (action.to_lat   != null) addMarker(action.to_lat,   action.to_lon   ?? 0, "#ff6b35");
            if (action.from_lat != null && action.to_lat != null) {
              const start = latLonToVec3(action.from_lat, action.from_lon ?? 0, EARTH_RADIUS);
              const end   = latLonToVec3(action.to_lat,   action.to_lon   ?? 0, EARTH_RADIUS);
              const mid   = start.clone().lerp(end, 0.5).normalize().multiplyScalar(EARTH_RADIUS * 1.5);
              const pts   = new THREE.QuadraticBezierCurve3(start, mid, end).getPoints(50);
              const line  = new THREE.Line(
                new THREE.BufferGeometry().setFromPoints(pts),
                new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.6 }),
              );
              s.routes.add(line);
              s.flight = { lat: ((action.from_lat + action.to_lat) / 2), lon: ((action.from_lon ?? 0) + (action.to_lon ?? 0)) / 2, dist: 350 };
            }
            if (targetRef.current)
              targetRef.current.textContent = `ROUTE : ${(action.from_name ?? "?").toUpperCase()} → ${(action.to_name ?? "?").toUpperCase()}`;
            break;
          }

          case "my_location":
            if (action.lat != null) {
              clearGroups();
              addMarker(action.lat, action.lon ?? 0, "#00ff88");
              s.flight = { lat: action.lat, lon: action.lon ?? 0, dist: 280 };
              if (targetRef.current) targetRef.current.textContent = "📍 VOTRE POSITION";
              if (coordsRef.current) coordsRef.current.textContent = `LAT ${action.lat.toFixed(4)}°  LON ${(action.lon ?? 0).toFixed(4)}°`;
            } else if (navigator.geolocation) {
              if (targetRef.current) targetRef.current.textContent = "📍 LOCALISATION...";
              navigator.geolocation.getCurrentPosition((pos) => {
                const mLat = pos.coords.latitude, mLon = pos.coords.longitude;
                clearGroups();
                addMarker(mLat, mLon, "#00ff88");
                if (sceneRef.current) sceneRef.current.flight = { lat: mLat, lon: mLon, dist: 280 };
                if (targetRef.current) targetRef.current.textContent = "📍 VOTRE POSITION";
                if (coordsRef.current) coordsRef.current.textContent = `LAT ${mLat.toFixed(4)}°  LON ${mLon.toFixed(4)}°`;
              });
            }
            break;

          case "hide":
            clearGroups();
            break;
        }
      },
    }));

    return (
      <div
        id="globe-overlay"
        style={{
          display:  isOpen ? "flex" : "none",
          opacity:  isOpen ? 1 : 0,
          transition: "opacity 0.6s ease",
        }}
      >
        <canvas ref={canvasRef} id="globe-canvas" />

        {/* Infos bas-centre */}
        <div className="globe-info">
          <div ref={targetRef} className="globe-target-label" />
          <div ref={coordsRef} className="globe-coords" />
        </div>

        {/* Bouton fermer */}
        <div className="globe-close-btn">
          <button className="hud-btn" onClick={onClose}>✕ FERMER</button>
        </div>

        {/* Tag Morphoz */}
        <div className="globe-morphoz-tag">MORPHOZ.IO</div>
      </div>
    );
  },
);

GlobeOverlay.displayName = "GlobeOverlay";
export default GlobeOverlay;
