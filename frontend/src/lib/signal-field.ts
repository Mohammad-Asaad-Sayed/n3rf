import {
  BufferAttribute,
  BufferGeometry,
  Color,
  OrthographicCamera,
  Points,
  PointsMaterial,
  Scene,
  WebGLRenderer,
} from "three";

export type SignalField = {
  render: (elapsed: number, aligned: boolean) => void;
  resize: () => void;
  dispose: () => void;
};

export function createSignalField(canvas: HTMLCanvasElement): SignalField {
  const bounds = canvas.getBoundingClientRect();
  const count = window.innerWidth < 900 ? 700 : 1800;
  const scene = new Scene();
  const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 20);
  camera.position.z = 8;

  const renderer = new WebGLRenderer({
    canvas,
    alpha: true,
    antialias: false,
    powerPreference: "low-power",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(bounds.width, bounds.height, false);
  renderer.setClearAlpha(0);

  const positions = new Float32Array(count * 3);
  const base = new Float32Array(count * 3);
  const lanes = new Float32Array(count);
  const aspect = bounds.width / bounds.height;
  const palette = [
    getComputedStyle(document.documentElement).getPropertyValue("--purple-light").trim(),
    getComputedStyle(document.documentElement).getPropertyValue("--info").trim(),
    getComputedStyle(document.documentElement).getPropertyValue("--text-tertiary").trim(),
  ].map((color) => new Color(color));
  const colors = new Float32Array(count * 3);

  for (let index = 0; index < count; index += 1) {
    const offset = index * 3;
    const x = aspect * (0.12 + Math.random() * 0.82);
    const y = Math.random() * 2 - 1;
    base[offset] = x;
    base[offset + 1] = y;
    positions[offset] = x;
    positions[offset + 1] = y;
    lanes[index] = Math.floor(Math.random() * 5) - 2;
    const color = palette[index % palette.length];
    colors[offset] = color.r;
    colors[offset + 1] = color.g;
    colors[offset + 2] = color.b;
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  geometry.setAttribute("color", new BufferAttribute(colors, 3));
  const material = new PointsMaterial({
    size: 2,
    sizeAttenuation: false,
    transparent: true,
    opacity: 0.56,
    vertexColors: true,
    depthWrite: false,
  });
  const points = new Points(geometry, material);
  scene.add(points);

  function resize() {
    const { width, height } = canvas.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.left = -(width / height);
    camera.right = width / height;
    camera.top = 1;
    camera.bottom = -1;
    camera.updateProjectionMatrix();
  }

  function render(elapsed: number, aligned: boolean) {
    const position = geometry.getAttribute("position");
    const laneSpacing = 0.11;
    for (let index = 0; index < count; index += 1) {
      const offset = index * 3;
      const targetY = aligned ? lanes[index] * laneSpacing : base[offset + 1];
      position.array[offset] += (base[offset] - position.array[offset]) * 0.035;
      position.array[offset + 1] +=
        (targetY - position.array[offset + 1]) * (aligned ? 0.055 : 0.018);
    }
    position.needsUpdate = true;
    points.rotation.z = Math.sin(elapsed * 0.05236) * 0.015;
    points.position.y = Math.sin(elapsed * 0.05236) * 0.018;
    renderer.render(scene, camera);
  }

  function dispose() {
    geometry.dispose();
    material.dispose();
    renderer.dispose();
  }

  resize();
  return { render, resize, dispose };
}
