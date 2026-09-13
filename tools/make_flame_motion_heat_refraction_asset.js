const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const sourceNif = path.join(root, "$out", "Meshes", "Effects", "FlameThrowerProjectileSprayVaporizer01.nif");
const meshDir = path.join(root, "Data", "Meshes", "GunHeatHaze");
const textureDir = path.join(root, "Data", "Textures", "Effects");
const gradientDir = path.join(textureDir, "Gradients");

const targetNif = path.join(meshDir, "GunHeatFlameMotionHeatRefraction.nif");
const targetDiffuse = path.join(textureDir, "HeatClearVapor01.dds");
const targetGradient = path.join(gradientDir, "HeatNoFlamesGrad01.dds");

const vanillaDiffusePath = "textures\\Effects\\SmokeVapor01Tile.dds";
const heatDiffusePath = "textures\\Effects\\HeatClearVapor01.dds";
const vanillaGradientPath = "textures\\Effects\\Gradients\\FlameThrowerGrad01.dds";
const heatGradientPath = "textures\\Effects\\Gradients\\HeatNoFlamesGrad01.dds";

const config = {
  diffuseSize: 256,
  gradientWidth: 256,
  alphaScale: Number(process.env.GUNHEAT_ALPHA_SCALE ?? "1.0"),
  loopSeconds: Number(process.env.GUNHEAT_LOOP_SECONDS ?? "1.333"),
  controllerSeconds: Number(process.env.GUNHEAT_CONTROLLER_SECONDS ?? "3.333"),
  quickFadeSeconds: Number(process.env.GUNHEAT_QUICK_FADE_SECONDS ?? "0.067"),
};

function makeDdsHeader(width, height) {
  const header = Buffer.alloc(128);
  header.write("DDS ", 0, "ascii");
  header.writeUInt32LE(124, 4);
  header.writeUInt32LE(0x0002100f, 8);
  header.writeUInt32LE(height, 12);
  header.writeUInt32LE(width, 16);
  header.writeUInt32LE(width * 4, 20);
  header.writeUInt32LE(0, 24);
  header.writeUInt32LE(1, 28);
  header.writeUInt32LE(32, 76);
  header.writeUInt32LE(0x00000041, 80);
  header.writeUInt32LE(0, 84);
  header.writeUInt32LE(32, 88);
  header.writeUInt32LE(0x00ff0000, 92);
  header.writeUInt32LE(0x0000ff00, 96);
  header.writeUInt32LE(0x000000ff, 100);
  header.writeUInt32LE(0xff000000, 104);
  header.writeUInt32LE(0x00001000, 108);
  return header;
}

function clampByte(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function fract(value) {
  return value - Math.floor(value);
}

function hash2(x, y) {
  return fract(Math.sin(x * 127.1 + y * 311.7) * 43758.5453123);
}

function smoothstep(edge0, edge1, value) {
  const t = Math.max(0, Math.min(1, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

function valueNoise(u, v, cells) {
  const x = u * cells;
  const y = v * cells;
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const tx = smoothstep(0, 1, fract(x));
  const ty = smoothstep(0, 1, fract(y));
  const a = hash2(x0, y0);
  const b = hash2(x0 + 1, y0);
  const c = hash2(x0, y0 + 1);
  const d = hash2(x0 + 1, y0 + 1);
  const ab = a + (b - a) * tx;
  const cd = c + (d - c) * tx;
  return ab + (cd - ab) * ty;
}

function writeDds(filePath, width, height, pixelFn) {
  const pixels = Buffer.alloc(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const [r, g, b, a] = pixelFn(x, y, width, height);
      const offset = (y * width + x) * 4;
      pixels[offset] = clampByte(b);
      pixels[offset + 1] = clampByte(g);
      pixels[offset + 2] = clampByte(r);
      pixels[offset + 3] = clampByte(a);
    }
  }
  fs.writeFileSync(filePath, Buffer.concat([makeDdsHeader(width, height), pixels]));
}

function heatFlowPixel(x, y, width, height) {
  const u = (x + 0.5) / width;
  const v = (y + 0.5) / height;
  const centered = Math.abs(u - 0.5) * 2;
  const vertical = 1 - Math.abs(v - 0.48) * 1.25;
  const barrelColumn = Math.max(0, 1 - Math.pow(centered, 1.55));
  const columnMask = Math.pow(barrelColumn, 1.8) * Math.max(0, vertical);

  const waveA = Math.sin((u * 5.5 + v * 3.2) * Math.PI * 2);
  const waveB = Math.sin((u * 12.0 - v * 4.6) * Math.PI * 2);
  const waveC = Math.sin((u * 2.0 + v * 9.5) * Math.PI * 2);
  const noise =
    valueNoise(u + Math.sin(v * Math.PI * 2) * 0.055, v, 8) * 0.50 +
    valueNoise(u * 1.6, v * 1.2, 18) * 0.32 +
    valueNoise(u * 3.0, v * 2.8, 34) * 0.18;

  const ripple = Math.max(0, 0.38 + waveA * 0.25 + waveB * 0.14 + waveC * 0.10 + (noise - 0.5) * 0.9);
  const topLift = smoothstep(0.08, 0.50, v) * (1 - smoothstep(0.93, 1.0, v));
  const alpha = clampByte(Math.pow(columnMask, 1.35) * Math.pow(ripple, 1.15) * topLift * 78 * config.alphaScale);

  const tone = clampByte(128 + ripple * 34 + noise * 20);
  return [tone, tone + 2, tone + 5, alpha];
}

function heatGradientPixel(x, y, width) {
  const t = x / Math.max(1, width - 1);
  const center = 1 - Math.abs(t - 0.5) * 2;
  const core = Math.pow(Math.max(0, center), 0.72);
  const shoulder = Math.sin(t * Math.PI);
  const alpha = clampByte((core * 52 + shoulder * 18) * config.alphaScale);
  const tone = clampByte(122 + core * 52);
  return [tone, tone + 2, tone + 5, alpha];
}

function replaceAllSameLength(buffer, from, to) {
  const fromBytes = Buffer.from(from, "ascii");
  const toBytes = Buffer.from(to, "ascii");
  if (fromBytes.length !== toBytes.length) {
    throw new Error(`Replacement length mismatch: ${fromBytes.length} -> ${toBytes.length}: ${from} -> ${to}`);
  }

  let count = 0;
  let index = buffer.indexOf(fromBytes);
  while (index !== -1) {
    toBytes.copy(buffer, index);
    count += 1;
    index = buffer.indexOf(fromBytes, index + toBytes.length);
  }
  return count;
}

function patchFloat32All(buffer, oldValue, newValue) {
  if (Math.abs(oldValue - newValue) < 0.00001) {
    return 0;
  }

  const from = Buffer.alloc(4);
  const to = Buffer.alloc(4);
  from.writeFloatLE(oldValue, 0);
  to.writeFloatLE(newValue, 0);

  let count = 0;
  let index = buffer.indexOf(from);
  while (index !== -1) {
    to.copy(buffer, index);
    count += 1;
    index = buffer.indexOf(from, index + 4);
  }
  return count;
}

fs.mkdirSync(meshDir, { recursive: true });
fs.mkdirSync(textureDir, { recursive: true });
fs.mkdirSync(gradientDir, { recursive: true });

writeDds(targetDiffuse, config.diffuseSize, config.diffuseSize, heatFlowPixel);
writeDds(targetGradient, config.gradientWidth, 1, heatGradientPixel);

const nif = Buffer.from(fs.readFileSync(sourceNif));
const diffuseReplacements = replaceAllSameLength(nif, vanillaDiffusePath, heatDiffusePath);
const gradientReplacements = replaceAllSameLength(nif, vanillaGradientPath, heatGradientPath);

if (diffuseReplacements === 0 || gradientReplacements === 0) {
  throw new Error(`Missing expected texture path replacement: diffuse=${diffuseReplacements}, gradient=${gradientReplacements}`);
}

const timingPatches = {
  loopSeconds: patchFloat32All(nif, 1.333, config.loopSeconds),
  controllerSeconds: patchFloat32All(nif, 3.333, config.controllerSeconds),
  quickFadeSeconds: patchFloat32All(nif, 0.067, config.quickFadeSeconds),
};

fs.writeFileSync(targetNif, nif);

console.log(
  JSON.stringify(
    {
      sourceNif,
      targetNif,
      targetDiffuse,
      targetGradient,
      diffuseReplacements,
      gradientReplacements,
      timingPatches,
      config,
      targetNifBytes: fs.statSync(targetNif).size,
      targetDiffuseBytes: fs.statSync(targetDiffuse).size,
      targetGradientBytes: fs.statSync(targetGradient).size,
    },
    null,
    2,
  ),
);
